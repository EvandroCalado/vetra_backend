from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from src.account.models import User
from src.account.repositories import TokenRepository, UserRepository
from src.account.services import AccountService
from src.account.utils import decode_token
from src.db.config import SessionDep


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_token_repository(session: SessionDep) -> TokenRepository:
    return TokenRepository(session)


def get_account_service(
    user_repo: UserRepositoryDep, token_repo: TokenRepositoryDep
) -> AccountService:
    return AccountService(user_repo, token_repo)


async def get_current_user(
    session: SessionDep, user_repo: UserRepositoryDep, request: Request
):
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

    user = await user_repo.get_by_id(int(user_id))

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


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
TokenRepositoryDep = Annotated[TokenRepository, Depends(get_token_repository)]
AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
AdminUserDep = Annotated[User, Depends(required_admin)]
