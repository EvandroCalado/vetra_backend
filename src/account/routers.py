from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from src.account.deps import AccountServiceDep, CurrentUserDep
from src.account.schemas import (
    PasswordChange,
    UserLogin,
    UserOut,
    UserRegister,
)
from src.account.utils import create_tokens

router = APIRouter()


@router.post(
    '/register/', response_model=UserOut, status_code=status.HTTP_201_CREATED
)
async def register(service: AccountServiceDep, user: UserRegister):
    return await service.register(user)


@router.post('/login/')
async def login(service: AccountServiceDep, user_login: UserLogin):
    user = await service.login(user_login)

    tokens = await create_tokens(service.session, user)

    response = JSONResponse(content={'message': 'Login successful'})

    response.set_cookie(
        key='access_token',
        value=tokens['access_token'],
        httponly=True,
        secure=True,
        samesite='lax',
        max_age=60 * 5,  # 5 minutes
    )

    response.set_cookie(
        key='refresh_token',
        value=tokens['refresh_token'],
        httponly=True,
        secure=True,
        samesite='lax',
        max_age=24 * 60 * 60 * 7,  # 7 days
    )

    return response


@router.get('/me/', response_model=UserOut)
async def me(current_user: CurrentUserDep):
    return current_user


@router.post('/refresh/')
async def refresh(service: AccountServiceDep, request: Request):
    user = await service.refresh(request)

    tokens = await create_tokens(service.session, user)

    response = JSONResponse(content={'message': 'Refresh successful'})

    response.set_cookie(
        key='access_token',
        value=tokens['access_token'],
        httponly=True,
        secure=True,
        samesite='lax',
        max_age=60 * 5,  # 5 minutes
    )

    response.set_cookie(
        key='refresh_token',
        value=tokens['refresh_token'],
        httponly=True,
        secure=True,
        samesite='lax',
        max_age=24 * 60 * 60 * 7,  # 7 days
    )

    return response


@router.post('/send-email-verification/')
async def send_email_verification(
    service: AccountServiceDep, current_user: CurrentUserDep
):
    return await service.send_email_verification(current_user)


@router.get('/verify-email/')
async def verify_email(service: AccountServiceDep, token: str):
    return await service.verify_email(token)


@router.post('/change-password/')
async def change_password(
    service: AccountServiceDep,
    current_user: CurrentUserDep,
    password_change: PasswordChange,
):
    return await service.change_password(current_user, password_change)
