import pytest
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings
from app.core.database import all_models
from app.main import app as main_app


@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    """Inicializa la conexión Beanie para la base de datos de pruebas."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)

    await init_beanie(
        database=client[settings.TEST_MONGODB_DB_NAME],
        document_models=all_models
    )

    # Inyectar el cliente global de la app para que routers (ej: health check) funcionen
    import app.core.database as db_module
    db_module.mongodb_client = client

    yield client

    # Limpieza al terminar toda la sesión de pruebas
    await client.drop_database(settings.TEST_MONGODB_DB_NAME)
    client.close()


@pytest.fixture(autouse=True)
async def clean_database():
    """Limpia todas las colecciones antes de cada caso de prueba."""
    for model in all_models:
        await model.delete_all()


@pytest.fixture
async def async_client():
    """Cliente HTTP asíncrono para pruebas de integración de rutas."""
    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as client:
        yield client
