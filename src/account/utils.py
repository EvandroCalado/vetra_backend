import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.models import RefreshToken, User
from src.db.settings import settings

pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=settings.JWT_ACCESS_TOKEN_TIME_MIN)
    )
    to_encode.update({'exp': expires})

    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


async def create_tokens(session: AsyncSession, user: User):
    access_token = create_access_token(data={'sub': str(user.id)})

    refresh_token_key = str(uuid.uuid4())
    refresh_token_expires = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_TIME_DAY
    )

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_key,
        expires_at=refresh_token_expires,
    )

    session.add(refresh_token)
    await session.commit()

    return {
        'access_token': access_token,
        'refresh_token': refresh_token_key,
        'token_type': 'bearer',
    }
