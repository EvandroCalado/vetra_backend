import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.config import get_db

# Importando models para garantir que eles sejam registrados no Base.metadata
from src.db.models import *  # noqa
from src.main import app

# Utilizaremos o banco de dados configurado no docker-compose.yml
DATABASE_URL_TEST = 'mysql+aiomysql://root:vetra@localhost:3307/vetra_test'

engine_test = create_async_engine(DATABASE_URL_TEST, echo=False, future=True)
async_session_test = async_sessionmaker(
    engine_test, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine_test.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with async_session_test() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='https://test'
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()
