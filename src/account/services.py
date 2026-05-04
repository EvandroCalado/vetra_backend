from fastapi import Request
from fastapi.responses import JSONResponse

from src.account.email import EmailProvider
from src.account.exceptions import (
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    OldPasswordMismatchError,
    RefreshTokenMissingError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.account.models import User
from src.account.repositories import TokenRepository, UserRepository
from src.account.schemas import (
    PasswordChange,
    PasswordReset,
    ResetPassword,
    UserLogin,
    UserOut,
    UserRegister,
)
from src.account.utils import (
    create_email_verification_token,
    create_password_reset_token,
    hash_password,
    verify_email_token_and_get_user_id,
    verify_password,
    verify_password_reset_token_and_get_user_id,
    verify_refresh_token,
)


class AccountService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: TokenRepository,
        email_provider: EmailProvider,
    ):
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.email_provider = email_provider

    async def register(self, user: UserRegister) -> UserOut:
        existing_user = await self.user_repository.get_by_email(user.email)

        if existing_user:
            raise UserAlreadyExistsError('Email already registered')

        new_user = await self.user_repository.create(
            user.email, hash_password(user.password)
        )

        return UserOut.model_validate(new_user)

    async def login(self, user_login: UserLogin) -> User:
        user = await self.user_repository.get_by_email(user_login.email)

        if not user or not verify_password(
            user_login.password, user.hashed_password
        ):
            raise InvalidCredentialsError('Invalid credentials')

        return user

    async def refresh(self, request: Request):
        token = request.cookies.get('refresh_token')

        if not token:
            raise RefreshTokenMissingError('Refresh token missing')

        user = await verify_refresh_token(self.token_repository, token)

        if not user:
            raise InvalidCredentialsError('Invalid or expired refresh token')

        return user

    async def send_email_verification(self, user: User):
        token = create_email_verification_token(user.id)
        link = (
            f'http://localhost:8000/api/v1/account/verify-email?token={token}'
        )

        await self.email_provider.send_verification_email(user.email, link)

        return {'message': 'Verification email send'}

    async def verify_email(self, token: str):
        user_id = verify_email_token_and_get_user_id(
            token, 'email_verification'
        )

        if not user_id:
            raise InvalidOrExpiredTokenError('Invalid or expired token')

        user = await self.user_repository.get_by_id(int(user_id))

        if not user:
            raise UserNotFoundError('User not found')

        user.is_verified = True

        await self.user_repository.save(user)

        return {'message': 'Email verified successfully'}

    async def change_password(
        self, user: User, password_change: PasswordChange
    ):
        is_valid_password = verify_password(
            password_change.old_password, user.hashed_password
        )

        if not is_valid_password:
            raise OldPasswordMismatchError('Old password is incorrect')

        user.hashed_password = hash_password(password_change.new_password)

        await self.user_repository.save(user)

        return {'message': 'Password changed successfully'}

    async def send_password_reset_email(self, reset_password: ResetPassword):
        user = await self.user_repository.get_by_email(reset_password.email)

        if not user:
            raise UserNotFoundError('User not found')

        token = create_password_reset_token(user.id)
        link = f'http://localhost:8000/api/v1/account/reset-password?token={token}'

        await self.email_provider.send_password_reset_email(user.email, link)

        return {'message': 'Password reset email send'}

    async def reset_password(self, password_reset: PasswordReset):
        user_id = verify_password_reset_token_and_get_user_id(
            password_reset.token, 'password_reset'
        )

        if not user_id:
            raise InvalidOrExpiredTokenError('Invalid or expired token')

        user = await self.user_repository.get_by_id(int(user_id))

        if not user:
            raise UserNotFoundError('User not found')

        user.hashed_password = hash_password(password_reset.new_password)

        await self.user_repository.save(user)

        return {'message': 'Password reset successfully'}

    async def logout(self, request: Request, user: User):
        refresh_token = request.cookies.get('refresh_token')

        if refresh_token:
            await self.token_repository.revoke(refresh_token)

        response = JSONResponse(content={'message': 'Logout successful'})
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')

        return response
