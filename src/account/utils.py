import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
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
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_TIME_MIN)
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


def decode_token(token: str):
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired',
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
        )


async def verify_refresh_token(session: AsyncSession, token: str):
    stmt = select(RefreshToken).where(RefreshToken.token == token)
    result = await session.execute(stmt)
    refresh_token = result.scalar_one_or_none()

    if refresh_token and not refresh_token.revoked:
        expires_at = refresh_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc):
            user_stmt = select(User).where(User.id == refresh_token.user_id)
            user_result = await session.scalars(user_stmt)
            return user_result.first()

    return None


def create_email_verification_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_VERIFICATION_TOKEN_TIME_HOURS
    )
    to_encode = {
        'sub': str(user_id),
        'exp': expires,
        'type': 'email_verification',
    }

    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def verify_email_token_and_get_user_id(token: str, token_type: str):
    payload = decode_token(token)

    if not payload or payload.get('type') != token_type:
        return None

    return payload.get('sub')


async def get_user_by_email(session: AsyncSession, email: str):
    stmt = select(User).where(User.email == email)
    result = await session.scalars(stmt)
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found'
        )

    return user


def create_password_reset_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_PASSWORD_RESET_TOKEN_TIME_HOURS
    )
    to_encode = {
        'sub': str(user_id),
        'exp': expires,
        'type': 'password_reset',
    }

    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def verify_password_reset_token_and_get_user_id(token: str, token_type: str):
    payload = decode_token(token)

    if not payload or payload.get('type') != token_type:
        return None

    return payload.get('sub')


async def revoke_refresh_token(session: AsyncSession, token: str):
    stmt = select(RefreshToken).where(RefreshToken.token == token)
    result = await session.execute(stmt)
    refresh_token = result.scalar_one_or_none()

    if refresh_token:
        refresh_token.revoked = True
        await session.commit()
