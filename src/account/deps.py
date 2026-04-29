from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select

from src.account.models import User
from src.account.services import AccountService
from src.account.utils import decode_token
from src.db.config import SessionDep


def get_account_service(session: SessionDep) -> AccountService:
    return AccountService(session)


async def get_current_user(session: SessionDep, request: Request):
    token = request.cookies.get('access_token')

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing access token',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user_id = payload.get('sub')

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    stmt = select(User).where(User.id == int(user_id))
    result = await session.scalars(stmt)
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    return user


async def required_admin(
    user: Annotated[User, Depends(get_current_user)],
):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Admin privileges required',
        )

    return user


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
AdminUserDep = Annotated[User, Depends(required_admin)]
