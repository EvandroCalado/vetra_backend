from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from jose import jwt

from src.account.utils import create_email_verification_token
from src.db.settings import settings


@pytest.mark.asyncio
async def test_verify_email_success(client: AsyncClient):
    payload = {
        'email': 'verify_action@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user to get the ID
    register_response = await client.post(
        '/api/v1/account/register/', json=payload
    )
    assert register_response.status_code == status.HTTP_201_CREATED
    user_id = register_response.json()['id']

    # Generate the valid token
    token = create_email_verification_token(user_id)

    # Call the verification endpoint
    response = await client.get(f'/api/v1/account/verify-email/?token={token}')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Email verified successfully'}

    # Verify the user is now active by logging in and checking /me/
    await client.post('/api/v1/account/login/', json=payload)
    me_response = await client.get('/api/v1/account/me/')
    assert me_response.json()['is_verified'] is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    response = await client.get(
        '/api/v1/account/verify-email/?token=invalid_token_string'
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Invalid or expired token'}


@pytest.mark.asyncio
async def test_verify_email_user_not_found(client: AsyncClient):
    # Generate a token for a user ID that doesn't exist
    token = create_email_verification_token(9999)

    response = await client.get(f'/api/v1/account/verify-email/?token={token}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'User not found'}


@pytest.mark.asyncio
async def test_verify_email_wrong_token_type(client: AsyncClient):

    # Generate a token with a different type
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {'sub': '1', 'exp': expires, 'type': 'wrong_type'}
    token = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    response = await client.get(f'/api/v1/account/verify-email/?token={token}')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Invalid or expired token'}
