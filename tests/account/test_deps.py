from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from jose import jwt

from src.db.settings import settings


def generate_custom_token(payload: dict):
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


@pytest.mark.asyncio
async def test_get_current_user_empty_payload(client: AsyncClient):
    # Empty payload evaluates to False in `if not payload:`
    token = generate_custom_token({})
    client.cookies.set('access_token', token)

    response = await client.get('/api/v1/account/me/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Invalid or expired token'}


@pytest.mark.asyncio
async def test_get_current_user_no_sub(client: AsyncClient):
    # Valid payload but missing 'sub' (user_id)
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    token = generate_custom_token({'exp': expires})
    client.cookies.set('access_token', token)

    response = await client.get('/api/v1/account/me/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Invalid token'}


@pytest.mark.asyncio
async def test_get_current_user_not_found(client: AsyncClient):
    # Payload with non-existent user id
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    token = generate_custom_token({'sub': '99999', 'exp': expires})
    client.cookies.set('access_token', token)

    response = await client.get('/api/v1/account/me/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Invalid token'}
