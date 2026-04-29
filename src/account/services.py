from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.models import User
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
    get_user_by_email,
    hash_password,
    verify_email_token_and_get_user_id,
    verify_password,
    verify_password_reset_token_and_get_user_id,
    verify_refresh_token,
)


class AccountService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, user: UserRegister) -> UserOut:
        stmt = select(User).where(User.email == user.email)
        result = await self.session.execute(stmt)

        if result.first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Email already registered',
            )

        new_user = User(
            email=user.email, hashed_password=hash_password(user.password)
        )

        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)

        return UserOut.model_validate(new_user)

    async def login(self, user_login: UserLogin) -> User:
        stmt = select(User).where(User.email == user_login.email)
        result = await self.session.scalars(stmt)
        user = result.first()

        if not user or not verify_password(
            user_login.password, user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid credentials',
            )

        return user

    async def refresh(self, request: Request):
        token = request.cookies.get('refresh_token')

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh token missing',
            )

        user = await verify_refresh_token(self.session, token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired refresh token',
            )

        return user

    @staticmethod
    async def send_email_verification(user: User):
        token = create_email_verification_token(user.id)
        link = f'http://localhost:8000/account/verify-email?token={token}'

        print(f'Email verification link: {link}')

        return {'message': 'Verification email send'}

    async def verify_email(self, token: str):
        user_id = verify_email_token_and_get_user_id(
            token, 'email_verification'
        )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid or expired token',
            )

        stmt = select(User).where(User.id == user_id)
        result = await self.session.scalars(stmt)
        user = result.first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='User not found'
            )

        user.is_verified = True

        self.session.add(user)
        await self.session.commit()

        return {'message': 'Email verified successfully'}

    async def change_password(
        self, user: User, password_change: PasswordChange
    ):
        is_valid_password = verify_password(
            password_change.old_password, user.hashed_password
        )

        if not is_valid_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Old password is incorrect',
            )

        user.hashed_password = hash_password(password_change.new_password)

        self.session.add(user)
        await self.session.commit()

        return {'message': 'Password changed successfully'}

    async def send_password_reset_email(self, reset_password: ResetPassword):
        user = await get_user_by_email(self.session, reset_password.email)

        token = create_password_reset_token(user.id)
        link = f'http://localhost:8000/account/reset-password?token={token}'

        print(f'Password reset link: {link}')

        return {'message': 'Password reset email send'}

    async def reset_password(self, password_reset: PasswordReset):
        user_id = verify_password_reset_token_and_get_user_id(
            password_reset.token, 'password_reset'
        )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid or expired token',
            )

        stmt = select(User).where(User.id == user_id)
        result = await self.session.scalars(stmt)
        user = result.first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='User not found'
            )

        user.hashed_password = hash_password(password_reset.new_password)

        self.session.add(user)
        await self.session.commit()

        return {'message': 'Password reset successfully'}
