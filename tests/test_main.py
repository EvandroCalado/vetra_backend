import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_is_running(client: AsyncClient):
    response = await client.get('/docs')
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_api_404(client: AsyncClient):
    response = await client.get('/non-existent-route')
    assert response.status_code == status.HTTP_404_NOT_FOUND
