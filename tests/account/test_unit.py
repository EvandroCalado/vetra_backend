import pytest
from datetime import datetime, timedelta, timezone

from src.account.exceptions import (
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.account.repositories import TokenRepository, UserRepository
from src.account.schemas import UserLogin, UserRegister
from src.account.services import AccountService
from src.account.utils import create_email_verification_token, create_password_reset_token


class MockUserRepository(UserRepository):
    def __init__(self):
        self.users = {}
        self._next_id = 1

    async def get_by_email(self, email: str):
        return self.users.get(email)

    async def get_by_id(self, id: int):
        for user in self.users.values():
            if user.id == id:
                return user
        return None

    async def create(self, email: str, hashed_password: str):
        user = type('User', (), {
            'id': self._next_id,
            'email': email,
            'hashed_password': hashed_password,
            'is_active': True,
            'is_admin': False,
            'is_verified': False,
        })()
        self.users[email] = user
        self._next_id += 1
        return user

    async def save(self, user):
        if user.email in self.users:
            self.users[user.email] = user
        return user


class MockTokenRepository(TokenRepository):
    def __init__(self, user_repo):
        self.tokens = {}
        self._user_repo = user_repo
        self.session = type('Session', (), {
            'get': lambda s, model, id: user_repo.get_by_id(id)
        })()

    async def create(self, user_id: int, token: str, expires_at):
        self.tokens[token] = {
            'user_id': user_id,
            'expires_at': expires_at,
            'revoked': False,
        }
        return type('RefreshToken', (), {
            'id': 1,
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at,
            'revoked': False,
            'session': self.session,
        })()

    async def get_by_token(self, token: str):
        if token in self.tokens:
            data = self.tokens[token]
            return type('RefreshToken', (), {
                'id': 1,
                'user_id': data['user_id'],
                'token': token,
                'expires_at': data['expires_at'],
                'revoked': data['revoked'],
                'session': self.session,
            })()
        return None

    async def revoke(self, token: str):
        if token in self.tokens:
            self.tokens[token]['revoked'] = True
            return True
        return False


@pytest.fixture
def mock_user_repo():
    return MockUserRepository()


@pytest.fixture
def mock_token_repo(mock_user_repo):
    return MockTokenRepository(mock_user_repo)


@pytest.fixture
def account_service(mock_user_repo, mock_token_repo):
    return AccountService(mock_user_repo, mock_token_repo)


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, account_service):
        user_reg = UserRegister(email='test@example.com', password='StrongPass123')

        result = await account_service.register(user_reg)

        assert result.email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, mock_user_repo, mock_token_repo):
        service = AccountService(mock_user_repo, mock_token_repo)

        user_reg = UserRegister(email='test@example.com', password='StrongPass123')
        await service.register(user_reg)

        with pytest.raises(UserAlreadyExistsError):
            await service.register(user_reg)


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, mock_user_repo, mock_token_repo):
        service = AccountService(mock_user_repo, mock_token_repo)

        await service.register(UserRegister(email='test@example.com', password='StrongPass123'))

        result = await service.login(UserLogin(email='test@example.com', password='StrongPass123'))

        assert result.email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, mock_user_repo, mock_token_repo):
        service = AccountService(mock_user_repo, mock_token_repo)

        await service.register(UserRegister(email='test@example.com', password='StrongPass123'))

        with pytest.raises(InvalidCredentialsError):
            await service.login(UserLogin(email='test@example.com', password='WrongPassword'))

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, mock_user_repo, mock_token_repo):
        service = AccountService(mock_user_repo, mock_token_repo)

        with pytest.raises(InvalidCredentialsError):
            await service.login(UserLogin(email='nonexistent@example.com', password='StrongPass123'))


class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_verify_email_success(self, mock_user_repo, mock_token_repo):
        service = AccountService(mock_user_repo, mock_token_repo)

        new_user = await mock_user_repo.create('test@example.com', 'hashed')
        token = create_email_verification_token(new_user.id)

        result = await service.verify_email(token)

        assert result['message'] == 'Email verified successfully'
        assert new_user.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, mock_user_repo, mock_token_repo):
        service = AccountService(mock_user_repo, mock_token_repo)

        with pytest.raises(InvalidOrExpiredTokenError):
            await service.verify_email('invalid_token')

    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(self, mock_user_repo, mock_token_repo):
        service = AccountService(mock_user_repo, mock_token_repo)

        token = create_email_verification_token(999)

        with pytest.raises(UserNotFoundError):
            await service.verify_email(token)


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_change_password_success(self, mock_user_repo, mock_token_repo):
        from src.account.schemas import PasswordChange
        from src.account.utils import hash_password

        service = AccountService(mock_user_repo, mock_token_repo)

        new_user = await mock_user_repo.create('test@example.com', hash_password('OldPass123'))
        old_hash = new_user.hashed_password

        result = await service.change_password(
            new_user,
            PasswordChange(old_password='OldPass123', new_password='NewPass456'),
        )

        assert result['message'] == 'Password changed successfully'
        assert new_user.hashed_password != old_hash

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, mock_user_repo, mock_token_repo):
        from src.account.schemas import PasswordChange
        from src.account.utils import hash_password

        service = AccountService(mock_user_repo, mock_token_repo)

        new_user = await mock_user_repo.create('test@example.com', hash_password('OldPass123'))

        from src.account.exceptions import OldPasswordMismatchError

        with pytest.raises(OldPasswordMismatchError):
            await service.change_password(
                new_user,
                PasswordChange(old_password='WrongPassword', new_password='NewPass456'),
            )


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_reset_password_success(self, mock_user_repo, mock_token_repo):
        from src.account.schemas import PasswordReset

        service = AccountService(mock_user_repo, mock_token_repo)

        new_user = await mock_user_repo.create('test@example.com', 'hashed')
        token = create_password_reset_token(new_user.id)

        result = await service.reset_password(
            PasswordReset(token=token, new_password='NewPass456'),
        )

        assert result['message'] == 'Password reset successfully'

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, mock_user_repo, mock_token_repo):
        from src.account.schemas import PasswordReset

        service = AccountService(mock_user_repo, mock_token_repo)

        with pytest.raises(InvalidOrExpiredTokenError):
            await service.reset_password(
                PasswordReset(token='invalid_token', new_password='NewPass456'),
            )

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self, mock_user_repo, mock_token_repo):
        from src.account.schemas import PasswordReset

        service = AccountService(mock_user_repo, mock_token_repo)

        token = create_password_reset_token(999)

        with pytest.raises(UserNotFoundError):
            await service.reset_password(
                PasswordReset(token=token, new_password='NewPass456'),
            )


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, mock_user_repo, mock_token_repo):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import MagicMock

        service = AccountService(mock_user_repo, mock_token_repo)

        new_user = await mock_user_repo.create('test@example.com', 'hashed')
        token = 'valid_refresh_token'
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        await mock_token_repo.create(new_user.id, token, expires)

        request = MagicMock()
        request.cookies.get.return_value = token

        result = await service.refresh(request)

        assert result.id == new_user.id

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, mock_user_repo, mock_token_repo):
        from unittest.mock import MagicMock
        from src.account.exceptions import RefreshTokenMissingError

        service = AccountService(mock_user_repo, mock_token_repo)

        request = MagicMock()
        request.cookies.get.return_value = None

        with pytest.raises(RefreshTokenMissingError):
            await service.refresh(request)

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, mock_user_repo, mock_token_repo):
        from unittest.mock import MagicMock
        from src.account.exceptions import InvalidCredentialsError

        service = AccountService(mock_user_repo, mock_token_repo)

        request = MagicMock()
        request.cookies.get.return_value = 'invalid_token'

        with pytest.raises(InvalidCredentialsError):
            await service.refresh(request)


class TestSendEmailVerification:
    @pytest.mark.asyncio
    async def test_send_email_verification(self, mock_user_repo, mock_token_repo):
        from src.account.services import AccountService

        new_user = await mock_user_repo.create('test@example.com', 'hashed')

        result = await AccountService.send_email_verification(new_user)

        assert result['message'] == 'Verification email send'


class TestSendPasswordResetEmail:
    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(self, mock_user_repo, mock_token_repo):
        from src.account.schemas import ResetPassword

        service = AccountService(mock_user_repo, mock_token_repo)

        await mock_user_repo.create('test@example.com', 'hashed')

        result = await service.send_password_reset_email(
            ResetPassword(email='test@example.com')
        )

        assert result['message'] == 'Password reset email send'

    @pytest.mark.asyncio
    async def test_send_password_reset_email_user_not_found(self, mock_user_repo, mock_token_repo):
        from src.account.schemas import ResetPassword

        service = AccountService(mock_user_repo, mock_token_repo)

        with pytest.raises(UserNotFoundError):
            await service.send_password_reset_email(
                ResetPassword(email='nonexistent@example.com')
            )


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_with_token(self, mock_user_repo, mock_token_repo):
        from unittest.mock import MagicMock
        from datetime import datetime, timedelta, timezone

        service = AccountService(mock_user_repo, mock_token_repo)

        new_user = await mock_user_repo.create('test@example.com', 'hashed')
        token = 'refresh_token_to_revoke'
        await mock_token_repo.create(new_user.id, token, datetime.now(timezone.utc) + timedelta(days=7))

        request = MagicMock()
        request.cookies.get.return_value = token

        response = await service.logout(request, new_user)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_without_token(self, mock_user_repo, mock_token_repo):
        from unittest.mock import MagicMock

        service = AccountService(mock_user_repo, mock_token_repo)

        new_user = await mock_user_repo.create('test@example.com', 'hashed')

        request = MagicMock()
        request.cookies.get.return_value = None

        response = await service.logout(request, new_user)

        assert response.status_code == 200


class TestTokenRepositoryRevoke:
    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self, mock_user_repo, mock_token_repo):
        result = await mock_token_repo.revoke('nonexistent_token')

        assert result is False
        assert 'nonexistent_token' not in mock_token_repo.tokens

    @pytest.mark.asyncio
    async def test_revoke_token_found(self, mock_user_repo, mock_token_repo):
        from datetime import datetime, timedelta, timezone

        new_user = await mock_user_repo.create('test@example.com', 'hashed')
        token = 'valid_token'
        await mock_token_repo.create(new_user.id, token, datetime.now(timezone.utc) + timedelta(days=7))

        result = await mock_token_repo.revoke(token)

        assert result is True
        assert mock_token_repo.tokens[token]['revoked'] is True


class TestUtils:
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, mock_user_repo):
        from src.account.utils import get_user_by_email

        await mock_user_repo.create('test@example.com', 'hashed')

        user = await get_user_by_email(mock_user_repo, 'test@example.com')

        assert user.email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, mock_user_repo):
        from src.account.utils import get_user_by_email
        from src.account.exceptions import UserNotFoundError

        with pytest.raises(UserNotFoundError):
            await get_user_by_email(mock_user_repo, 'nonexistent@example.com')

    @pytest.mark.asyncio
    async def test_revoke_refresh_token_success(self, mock_user_repo, mock_token_repo):
        from src.account.utils import revoke_refresh_token
        from datetime import datetime, timedelta, timezone

        new_user = await mock_user_repo.create('test@example.com', 'hashed')
        token = 'token_to_revoke'
        await mock_token_repo.create(new_user.id, token, datetime.now(timezone.utc) + timedelta(days=7))

        result = await revoke_refresh_token(mock_token_repo, token)

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_refresh_token_not_found(self, mock_user_repo, mock_token_repo):
        from src.account.utils import revoke_refresh_token

        result = await revoke_refresh_token(mock_token_repo, 'nonexistent_token')

        assert result is False