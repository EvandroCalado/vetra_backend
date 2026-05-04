import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import update

from src.account.models import User
from tests.conftest import async_session_test


@pytest.mark.asyncio
async def test_admin_success(client: AsyncClient):
    payload = {
        'email': 'admin_test@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/api/v1/account/register/', json=payload)

    # Make user an admin directly in the test database
    async with async_session_test() as session:
        await session.execute(
            update(User)
            .where(User.email == payload['email'])
            .values(is_admin=True)
        )
        await session.commit()

    # Login to get access token
    await client.post('/api/v1/account/login/', json=payload)

    # Call the admin endpoint
    response = await client.get('/api/v1/account/admin/')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'message': f'Hello, {payload["email"]}! You have admin access.'
    }


@pytest.mark.asyncio
async def test_admin_forbidden(client: AsyncClient):
    payload = {
        'email': 'regular_user@example.com',
        'password': 'StrongPassword123',
    }

    # Register and login a normal user
    await client.post('/api/v1/account/register/', json=payload)
    await client.post('/api/v1/account/login/', json=payload)

    # Attempt to access the admin endpoint
    response = await client.get('/api/v1/account/admin/')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Admin privileges required'}


@pytest.mark.asyncio
async def test_admin_unauthorized(client: AsyncClient):
    # Attempt to access without logging in
    response = await client.get('/api/v1/account/admin/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Missing access token'}
