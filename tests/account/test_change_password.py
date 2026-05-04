import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient):
    payload = {
        'email': 'changepass@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/api/v1/account/register/', json=payload)

    # Attempt login to get access token
    await client.post('/api/v1/account/login/', json=payload)

    # Change password
    change_payload = {
        'old_password': 'StrongPassword123',
        'new_password': 'NewStrongPassword456',
    }
    response = await client.post(
        '/api/v1/account/change-password/', json=change_payload
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Password changed successfully'}

    # Verify login works with the new password
    new_login_payload = {
        'email': 'changepass@example.com',
        'password': 'NewStrongPassword456',
    }
    new_login_response = await client.post(
        '/api/v1/account/login/', json=new_login_payload
    )
    assert new_login_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_change_password_unauthorized(client: AsyncClient):
    change_payload = {
        'old_password': 'StrongPassword123',
        'new_password': 'NewStrongPassword456',
    }
    response = await client.post(
        '/api/v1/account/change-password/', json=change_payload
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Missing access token'}


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(client: AsyncClient):
    payload = {
        'email': 'wrongoldpass@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user and login
    await client.post('/api/v1/account/register/', json=payload)
    await client.post('/api/v1/account/login/', json=payload)

    # Change password with wrong old password
    change_payload = {
        'old_password': 'WrongPassword123',
        'new_password': 'NewStrongPassword456',
    }
    response = await client.post(
        '/api/v1/account/change-password/', json=change_payload
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Old password is incorrect'}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('invalid_password', 'error_type'),
    [
        ('short', 'string_too_short'),  # length < 8
        ('nouppercase123', 'value_error'),  # no uppercase
        ('NOLOWERCASE123', 'value_error'),  # no lowercase
        ('NoDigitsHere', 'value_error'),  # no digits
    ],
)
async def test_change_password_invalid_new_password(
    client: AsyncClient, invalid_password, error_type
):
    payload = {
        'email': f'invalidnewpass_{invalid_password}@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user and login
    await client.post('/api/v1/account/register/', json=payload)
    await client.post('/api/v1/account/login/', json=payload)

    # Change password with invalid new password
    change_payload = {
        'old_password': 'StrongPassword123',
        'new_password': invalid_password,
    }
    response = await client.post(
        '/api/v1/account/change-password/', json=change_payload
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data['detail'][0]['loc'] == ['body', 'new_password']
    assert data['detail'][0]['type'] == error_type
