import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.account.email import EmailProvider
from src.account.exceptions import (
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    RefreshTokenMissingError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.account.repositories import TokenRepository, UserRepository
from src.account.schemas import PasswordChange, ResetPassword, UserLogin, UserRegister
from src.account.services import AccountService
from src.account.utils import create_email_verification_token, create_password_reset_token


class MockEmailProvider(EmailProvider):
    def __init__(self):
        self.sent_emails = []

    async def send_verification_email(self, to: str, link: str) -> None:
        self.sent_emails.append({'type': 'verification', 'to': to, 'link': link})

    async def send_password_reset_email(self, to: str, link: str) -> None:
        self.sent_emails.append({'type': 'password_reset', 'to': to, 'link': link})


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
    def __init__(self):
        self.tokens = {}
        self._session_get = None

    @property
    def session(self):
        class Session:
            def __init__(self, parent):
                self._parent = parent

            def get(self, model, id):
                if hasattr(self._parent, '_user_repo'):
                    return self._parent._user_repo.get_by_id(id)
                return None
        return Session(self)

    def set_user_repo(self, user_repo):
        self._user_repo = user_repo
        self.session  # refresh session

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
            })()
        return None

    async def revoke(self, token: str):
        if token in self.tokens:
            self.tokens[token]['revoked'] = True
            return True
        return False


class TestAccountService:
    @pytest.fixture
    def user_repo(self):
        return MockUserRepository()

    @pytest.fixture
    def token_repo(self, user_repo):
        repo = MockTokenRepository()
        repo.set_user_repo(user_repo)
        return repo

    @pytest.fixture
    def email_provider(self):
        return MockEmailProvider()

    @pytest.fixture
    def service(self, user_repo, token_repo, email_provider):
        return AccountService(user_repo, token_repo, email_provider)

    @pytest.mark.asyncio
    async def test_register_success(self, service):
        result = await service.register(UserRegister(email='test@example.com', password='StrongPass123'))
        assert result.email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        await svc.register(UserRegister(email='test@example.com', password='StrongPass123'))
        with pytest.raises(UserAlreadyExistsError):
            await svc.register(UserRegister(email='test@example.com', password='StrongPass123'))

    @pytest.mark.asyncio
    async def test_login_success(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        await svc.register(UserRegister(email='test@example.com', password='StrongPass123'))
        user = await svc.login(UserLogin(email='test@example.com', password='StrongPass123'))
        assert user.email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        await svc.register(UserRegister(email='test@example.com', password='StrongPass123'))
        with pytest.raises(InvalidCredentialsError):
            await svc.login(UserLogin(email='test@example.com', password='WrongPass123'))

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        with pytest.raises(InvalidCredentialsError):
            await svc.login(UserLogin(email='nobody@example.com', password='StrongPass123'))

    @pytest.mark.asyncio
    async def test_verify_email_success(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', 'hashed')
        token = create_email_verification_token(user.id)
        result = await svc.verify_email(token)
        assert result['message'] == 'Email verified successfully'
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, service):
        with pytest.raises(InvalidOrExpiredTokenError):
            await service.verify_email('invalid_token')

    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(self, service):
        token = create_email_verification_token(999)
        with pytest.raises(UserNotFoundError):
            await service.verify_email(token)

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_repo, token_repo, email_provider):
        from src.account.utils import hash_password
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', hash_password('OldPass123'))
        old_hash = user.hashed_password
        result = await svc.change_password(user, PasswordChange(old_password='OldPass123', new_password='NewPass123'))
        assert result['message'] == 'Password changed successfully'
        assert user.hashed_password != old_hash

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, user_repo, token_repo, email_provider):
        from src.account.exceptions import OldPasswordMismatchError
        from src.account.utils import hash_password
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', hash_password('OldPass123'))
        with pytest.raises(OldPasswordMismatchError):
            await svc.change_password(user, PasswordChange(old_password='WrongPass', new_password='NewPass123'))

    @pytest.mark.asyncio
    async def test_reset_password_success(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', 'hashed')
        token = create_password_reset_token(user.id)
        result = await svc.reset_password(type('Reset', (), {'token': token, 'new_password': 'NewPass123'})())
        assert result['message'] == 'Password reset successfully'

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, service):
        class FakeReset:
            token = 'invalid'
            new_password = 'NewPass123'
        with pytest.raises(InvalidOrExpiredTokenError):
            await service.reset_password(FakeReset())

    @pytest.mark.asyncio
    async def test_refresh_success(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', 'hashed')
        token = 'valid_refresh_token'
        await token_repo.create(user.id, token, datetime.now(timezone.utc) + timedelta(days=7))
        request = MagicMock()
        request.cookies.get.return_value = token
        result = await svc.refresh(request)
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        request = MagicMock()
        request.cookies.get.return_value = None
        with pytest.raises(RefreshTokenMissingError):
            await svc.refresh(request)

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        request = MagicMock()
        request.cookies.get.return_value = 'invalid_token'
        with pytest.raises(InvalidCredentialsError):
            await svc.refresh(request)

    @pytest.mark.asyncio
    async def test_send_email_verification(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', 'hashed')
        result = await svc.send_email_verification(user)
        assert result['message'] == 'Verification email send'
        assert len(email_provider.sent_emails) == 1
        assert email_provider.sent_emails[0]['type'] == 'verification'

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        await user_repo.create('test@example.com', 'hashed')
        result = await svc.send_password_reset_email(ResetPassword(email='test@example.com'))
        assert result['message'] == 'Password reset email send'
        assert len(email_provider.sent_emails) == 1
        assert email_provider.sent_emails[0]['type'] == 'password_reset'

    @pytest.mark.asyncio
    async def test_send_password_reset_email_not_found(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        with pytest.raises(UserNotFoundError):
            await svc.send_password_reset_email(ResetPassword(email='nobody@example.com'))

    @pytest.mark.asyncio
    async def test_logout_with_token(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', 'hashed')
        token = 'refresh_token'
        await token_repo.create(user.id, token, datetime.now(timezone.utc) + timedelta(days=7))
        request = MagicMock()
        request.cookies.get.return_value = token
        response = await svc.logout(request, user)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_without_token(self, user_repo, token_repo, email_provider):
        svc = AccountService(user_repo, token_repo, email_provider)
        user = await user_repo.create('test@example.com', 'hashed')
        request = MagicMock()
        request.cookies.get.return_value = None
        response = await svc.logout(request, user)
        assert response.status_code == 200


class TestTokenRepository:
    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self):
        repo = MockTokenRepository()
        result = await repo.revoke('nonexistent')
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_token_found(self):
        repo = MockTokenRepository()
        await repo.create(1, 'token', datetime.now(timezone.utc) + timedelta(days=7))
        result = await repo.revoke('token')
        assert result is True


class TestEmailProvider:
    @pytest.mark.asyncio
    async def test_email_provider_abc_cannot_instantiate(self):
        from src.account.email import EmailProvider
        with pytest.raises(TypeError):
            EmailProvider()

    @pytest.mark.asyncio
    async def test_smtp_provider_not_implemented(self):
        from src.account.email import SMTPEmailProvider
        provider = SMTPEmailProvider()
        with pytest.raises(NotImplementedError):
            await provider.send_verification_email('test@example.com', 'http://link')

    @pytest.mark.asyncio
    async def test_smtp_provider_not_implemented_password_reset(self):
        from src.account.email import SMTPEmailProvider
        provider = SMTPEmailProvider()
        with pytest.raises(NotImplementedError):
            await provider.send_password_reset_email('test@example.com', 'http://link')
    @pytest.mark.asyncio
    async def test_get_user_by_email(self):
        user_repo = MockUserRepository()
        await user_repo.create('test@example.com', 'hashed')
        from src.account.utils import get_user_by_email
        user = await get_user_by_email(user_repo, 'test@example.com')
        assert user.email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        user_repo = MockUserRepository()
        from src.account.utils import get_user_by_email
        with pytest.raises(UserNotFoundError):
            await get_user_by_email(user_repo, 'nobody@example.com')

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self):
        token_repo = MockTokenRepository()
        await token_repo.create(1, 'token', datetime.now(timezone.utc) + timedelta(days=7))
        from src.account.utils import revoke_refresh_token
        result = await revoke_refresh_token(token_repo, 'token')
        assert result is True