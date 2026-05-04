import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_email_verification_success(client: AsyncClient):
    payload = {
        'email': 'verify_test@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/api/v1/account/register/', json=payload)

    # Attempt login to get access token
    login_response = await client.post('/api/v1/account/login/', json=payload)
    assert login_response.status_code == status.HTTP_200_OK

    # Client automatically stores cookies, so we can directly call the endpoint
    response = await client.post('/api/v1/account/send-email-verification/')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Verification email send'}


@pytest.mark.asyncio
async def test_send_email_verification_unauthorized(client: AsyncClient):
    # Call endpoint without any cookies
    response = await client.post('/api/v1/account/send-email-verification/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Missing access token'}
