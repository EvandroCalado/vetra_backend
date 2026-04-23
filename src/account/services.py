from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.models import User
from src.account.schemas import UserCreate
from src.account.utils import hash_password


async def create_user(session: AsyncSession, user: UserCreate):
    stmt = select(User).where(User.email == user.email)
    result = await session.execute(stmt)

    if result.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Email already registered',
        )

    new_user = User(
        email=user.email, hashed_password=hash_password(user.password)
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user
