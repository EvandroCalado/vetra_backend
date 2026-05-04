import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient):
    payload = {
        'email': 'refresh_test@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/api/v1/account/register/', json=payload)

    # Attempt login to get tokens
    login_response = await client.post('/api/v1/account/login/', json=payload)
    assert login_response.status_code == status.HTTP_200_OK

    # Call refresh endpoint
    # The client automatically sends the cookies (refresh_token)
    response = await client.post('/api/v1/account/refresh/')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Refresh successful'}

    # Check if new cookies are set
    cookies = response.cookies
    assert 'access_token' in cookies
    assert 'refresh_token' in cookies


@pytest.mark.asyncio
async def test_refresh_missing_token(client: AsyncClient):
    # Call /refresh/ without any cookies
    response = await client.post('/api/v1/account/refresh/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Refresh token missing'}


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    # Set a fake refresh token
    client.cookies.set('refresh_token', 'fake-uuid-or-invalid-token')

    response = await client.post('/api/v1/account/refresh/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Invalid or expired refresh token'}
