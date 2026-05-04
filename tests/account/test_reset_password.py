from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from jose import jwt

from src.account.utils import create_password_reset_token
from src.db.settings import settings


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient):
    payload = {
        'email': 'resetpass_success@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user to get the ID
    register_response = await client.post(
        '/api/v1/account/register/', json=payload
    )
    assert register_response.status_code == status.HTTP_201_CREATED
    user_id = register_response.json()['id']

    # Generate the valid token
    token = create_password_reset_token(user_id)

    # Call the reset password endpoint
    reset_payload = {'token': token, 'new_password': 'NewStrongPassword456'}
    response = await client.post(
        '/api/v1/account/reset-password/', json=reset_payload
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Password reset successfully'}

    # Verify login works with the new password
    new_login_payload = {
        'email': 'resetpass_success@example.com',
        'password': 'NewStrongPassword456',
    }
    new_login_response = await client.post(
        '/api/v1/account/login/', json=new_login_payload
    )
    assert new_login_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    reset_payload = {
        'token': 'invalid_token_string',
        'new_password': 'NewStrongPassword456',
    }
    response = await client.post(
        '/api/v1/account/reset-password/', json=reset_payload
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Invalid or expired token'}


@pytest.mark.asyncio
async def test_reset_password_user_not_found(client: AsyncClient):
    # Generate a token for a user ID that doesn't exist
    token = create_password_reset_token(9999)

    reset_payload = {'token': token, 'new_password': 'NewStrongPassword456'}
    response = await client.post(
        '/api/v1/account/reset-password/', json=reset_payload
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'User not found'}


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
async def test_reset_password_invalid_new_password(
    client: AsyncClient, invalid_password, error_type
):
    payload = {
        'email': f'invalidreset_{invalid_password}@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    register_response = await client.post(
        '/api/v1/account/register/', json=payload
    )
    user_id = register_response.json()['id']
    token = create_password_reset_token(user_id)

    # Attempt to reset with invalid password
    reset_payload = {
        'token': token,
        'new_password': invalid_password,
    }
    response = await client.post(
        '/api/v1/account/reset-password/', json=reset_payload
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data['detail'][0]['loc'] == ['body', 'new_password']
    assert data['detail'][0]['type'] == error_type


@pytest.mark.asyncio
async def test_reset_password_wrong_token_type(client: AsyncClient):

    # Generate a token with a different type
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {'sub': '1', 'exp': expires, 'type': 'wrong_type'}
    token = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    reset_payload = {
        'token': token,
        'new_password': 'NewStrongPassword123',
    }
    response = await client.post(
        '/api/v1/account/reset-password/', json=reset_payload
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Invalid or expired token'}
