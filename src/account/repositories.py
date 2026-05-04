from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.models import RefreshToken, User

if TYPE_CHECKING:
    from src.account.models import RefreshToken, User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> 'User | None':
        stmt = select(User).where(User.email == email)
        result = await self.session.scalars(stmt)
        return result.first()

    async def get_by_id(self, id: int) -> 'User | None':
        stmt = select(User).where(User.id == id)
        result = await self.session.scalars(stmt)
        return result.first()

    async def create(self, email: str, hashed_password: str) -> 'User':
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def save(self, user: 'User') -> 'User':
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user


class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, user_id: int, token: str, expires_at: datetime
    ) -> 'RefreshToken':
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_by_token(self, token: str) -> 'RefreshToken | None':
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> bool:
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.session.execute(stmt)
        refresh_token = result.scalar_one_or_none()

        if refresh_token:
            refresh_token.revoked = True
            await self.session.commit()
            return True

        return False
