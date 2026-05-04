import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_password_reset_email_success(client: AsyncClient):
    payload = {
        'email': 'reset_email_test@example.com',
        'password': 'StrongPassword123',
    }

    # Pre-register user
    await client.post('/api/v1/account/register/', json=payload)

    # Request password reset email
    reset_payload = {'email': payload['email']}
    response = await client.post(
        '/api/v1/account/send-password-reset-email/', json=reset_payload
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Password reset email send'}


@pytest.mark.asyncio
async def test_send_password_reset_email_not_found(client: AsyncClient):
    reset_payload = {'email': 'nonexistent_user@example.com'}
    response = await client.post(
        '/api/v1/account/send-password-reset-email/', json=reset_payload
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'User not found'}


@pytest.mark.asyncio
async def test_send_password_reset_email_invalid_payload(client: AsyncClient):
    reset_payload = {'email': 'invalid-email-format'}
    response = await client.post(
        '/api/v1/account/send-password-reset-email/', json=reset_payload
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data['detail'][0]['loc'] == ['body', 'email']
    assert data['detail'][0]['type'] == 'value_error'
