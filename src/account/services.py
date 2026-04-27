from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.models import User
from src.account.schemas import UserLogin, UserOut, UserRegister
from src.account.utils import (
    hash_password,
    verify_password,
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
