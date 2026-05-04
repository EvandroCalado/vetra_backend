import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.config import get_db


@pytest.mark.asyncio
async def test_get_db():
    # Call the async generator
    generator = get_db()

    # Get the first (and only) yielded value
    session = await anext(generator)

    # Verify it yielded an AsyncSession
    assert isinstance(session, AsyncSession)

    # Cleanup: iterate to close the generator properly
    with pytest.raises(StopAsyncIteration):
        await anext(generator)
