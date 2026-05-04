import pytest
from datetime import datetime, timedelta, timezone

from src.account.repositories import TokenRepository, UserRepository
from src.account.models import RefreshToken, User
from src.db.config import async_session


class TestUserRepositoryIntegration:
    @pytest.mark.asyncio
    async def test_user_repository_get_by_email(self, db_session):
        repo = UserRepository(db_session)

        user = await repo.create('test@example.com', 'hashed_password')

        result = await repo.get_by_email('test@example.com')

        assert result is not None
        assert result.email == 'test@example.com'

    @pytest.mark.asyncio
    async def test_user_repository_get_by_id(self, db_session):
        repo = UserRepository(db_session)

        user = await repo.create('test@example.com', 'hashed_password')

        result = await repo.get_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_user_repository_save(self, db_session):
        repo = UserRepository(db_session)

        user = await repo.create('test@example.com', 'hashed_password')
        user.is_verified = True

        saved_user = await repo.save(user)

        assert saved_user.is_verified is True


class TestTokenRepositoryIntegration:
    @pytest.mark.asyncio
    async def test_token_repository_create(self, db_session):
        user_repo = UserRepository(db_session)
        token_repo = TokenRepository(db_session)

        user = await user_repo.create('test@example.com', 'hashed')

        token = await token_repo.create(
            user.id, 'test_token', datetime.now(timezone.utc) + timedelta(days=7)
        )

        assert token is not None
        assert token.token == 'test_token'

    @pytest.mark.asyncio
    async def test_token_repository_get_by_token(self, db_session):
        user_repo = UserRepository(db_session)
        token_repo = TokenRepository(db_session)

        user = await user_repo.create('test@example.com', 'hashed')

        await token_repo.create(
            user.id, 'test_token', datetime.now(timezone.utc) + timedelta(days=7)
        )

        result = await token_repo.get_by_token('test_token')

        assert result is not None
        assert result.token == 'test_token'

    @pytest.mark.asyncio
    async def test_token_repository_revoke(self, db_session):
        user_repo = UserRepository(db_session)
        token_repo = TokenRepository(db_session)

        user = await user_repo.create('test@example.com', 'hashed')

        await token_repo.create(
            user.id, 'test_token', datetime.now(timezone.utc) + timedelta(days=7)
        )

        result = await token_repo.revoke('test_token')

        assert result is True

    @pytest.mark.asyncio
    async def test_token_repository_revoke_not_found(self, db_session):
        user_repo = UserRepository(db_session)
        token_repo = TokenRepository(db_session)

        user = await user_repo.create('test@example.com', 'hashed')

        result = await token_repo.revoke('nonexistent_token')

        assert result is False