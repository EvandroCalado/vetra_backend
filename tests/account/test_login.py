import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    payload = {
        'email': 'login_test@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/account/register/', json=payload)

    # Attempt login
    response = await client.post('/account/login/', json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Login successful'}

    # Check if cookies are set
    cookies = response.cookies
    assert 'access_token' in cookies
    assert 'refresh_token' in cookies


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    payload = {
        'email': 'login_wrongpass@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/account/register/', json=payload)

    # Attempt login with wrong password
    wrong_payload = {
        'email': 'login_wrongpass@example.com',
        'password': 'WrongPassword123',
    }
    response = await client.post('/account/login/', json=wrong_payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Invalid credentials'}


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    payload = {
        'email': 'notfound@example.com',
        'password': 'StrongPassword123',
    }

    # Attempt login without registering
    response = await client.post('/account/login/', json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Invalid credentials'}


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient):
    # Attempt login with missing password
    payload = {'email': 'missing@example.com'}
    response = await client.post('/account/login/', json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data['detail'][0]['loc'] == ['body', 'password']
    assert data['detail'][0]['type'] == 'missing'
