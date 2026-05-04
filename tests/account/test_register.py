import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    payload = {
        'email': 'testuser@example.com',
        'password': 'StrongPassword123',
    }
    response = await client.post('/account/register/', json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data['email'] == payload['email']
    assert 'id' in data
    assert data['is_active'] is True
    assert data['is_admin'] is False
    assert data['is_verified'] is False
    assert 'password' not in data
    assert 'hashed_password' not in data


@pytest.mark.asyncio
async def test_register_existing_email(client: AsyncClient):
    payload = {
        'email': 'existinguser@example.com',
        'password': 'StrongPassword123',
    }

    # First registration should succeed
    response = await client.post('/account/register/', json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    # Second registration with the same email should fail
    response_duplicate = await client.post('/account/register/', json=payload)
    assert response_duplicate.status_code == status.HTTP_404_NOT_FOUND
    assert response_duplicate.json() == {'detail': 'Email already registered'}


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    payload = {'email': 'not-an-email', 'password': 'StrongPassword123'}
    response = await client.post('/account/register/', json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data['detail'][0]['loc'] == ['body', 'email']
    assert data['detail'][0]['type'] == 'value_error'


@pytest.mark.asyncio
async def test_register_missing_fields(client: AsyncClient):
    payload = {'email': 'missingpassword@example.com'}
    response = await client.post('/account/register/', json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data['detail'][0]['loc'] == ['body', 'password']
    assert data['detail'][0]['type'] == 'missing'
