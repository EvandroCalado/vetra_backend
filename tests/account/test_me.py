from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from jose import jwt

from src.db.settings import settings


@pytest.mark.asyncio
async def test_me_success(client: AsyncClient):
    payload = {'email': 'me_test@example.com', 'password': 'StrongPassword123'}

    # Pre-register user
    await client.post('/account/register/', json=payload)

    # Attempt login
    login_response = await client.post('/account/login/', json=payload)
    assert login_response.status_code == status.HTTP_200_OK

    # client automatically stores cookies (including access_token)
    response = await client.get('/account/me/')

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data['email'] == payload['email']
    assert 'id' in data
    assert 'password' not in data


@pytest.mark.asyncio
async def test_me_unauthorized_missing_token(client: AsyncClient):
    # Call /me/ without any cookies
    response = await client.get('/account/me/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Missing access token'}


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    client.cookies.set('access_token', 'fake.invalid.token')
    response = await client.get('/account/me/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Invalid token'}


@pytest.mark.asyncio
async def test_me_expired_token(client: AsyncClient):

    # Generate a token that expired 1 hour ago
    expires = datetime.now(timezone.utc) - timedelta(hours=1)
    to_encode = {'sub': '1', 'exp': expires}
    expired_token = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    client.cookies.set('access_token', expired_token)
    response = await client.get('/account/me/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Token has expired'}
