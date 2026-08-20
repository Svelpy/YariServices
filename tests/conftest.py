import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from app.core.config import Settings, get_settings
from app.core.database import initialize_beanie


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        ENVIRONMENT="test",
        MONGODB_URL="mongodb://localhost:27017",
        MONGODB_DB_NAME="yari_test",
        TEST_MONGODB_DB_NAME="yari_test",
        SECRET_KEY="test-secret-key",
        REDIS_URL="redis://localhost:6379/15",
        DEV_ORIGINS="http://localhost:5173",
    )


@pytest_asyncio.fixture
async def test_db():
    """Base real para pruebas de integración; no se activa automáticamente."""
    settings = get_settings()
    client = AsyncMongoClient(settings.MONGODB_URL)
    database = client.get_database(settings.TEST_MONGODB_DB_NAME)

    await database.command("ping")
    await initialize_beanie(database, settings)

    try:
        yield database
    finally:
        await database.client.drop_database(database.name)
        await client.close()
