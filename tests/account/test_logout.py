import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient):
    payload = {
        'email': 'logout_test@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/account/register/', json=payload)

    # Login to get access token and refresh token
    login_response = await client.post('/account/login/', json=payload)
    assert login_response.status_code == status.HTTP_200_OK

    # Capture the refresh token before logout
    refresh_token = client.cookies.get('refresh_token')

    # Call the logout endpoint
    response = await client.post('/account/logout/')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Logout successful'}

    # Verify that cookies are deleted
    assert 'access_token' not in client.cookies
    assert 'refresh_token' not in client.cookies

    # Verify the refresh token is actually revoked in the database
    # by trying to use it in the /refresh/ endpoint
    client.cookies.set('refresh_token', refresh_token)
    refresh_response = await client.post('/account/refresh/')

    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert refresh_response.json() == {
        'detail': 'Invalid or expired refresh token'
    }


@pytest.mark.asyncio
async def test_logout_unauthorized(client: AsyncClient):
    # Attempt to logout without being logged in (no cookies)
    response = await client.post('/account/logout/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Missing access token'}
