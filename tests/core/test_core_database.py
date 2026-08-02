from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.database as db_module
from app.core.database import close_mongo_connection, connect_to_mongo


@pytest.fixture(autouse=True)
def reset_mongodb_client():
    """Restaura el cliente global a None antes y después de cada test."""
    db_module.mongodb_client = None
    yield
    db_module.mongodb_client = None


class TestConnectToMongo:
    """Tests para connect_to_mongo (todo mockeado — sin conexión real)."""

    @pytest.mark.asyncio
    async def test_crea_motor_client_con_url_correcta(self):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock()

        with (
            patch("app.core.database.AsyncIOMotorClient", return_value=mock_client) as mock_cls,
            patch("app.core.database.init_beanie", new_callable=AsyncMock),
            patch("app.core.database.settings") as mock_settings,
        ):
            mock_settings.MONGODB_URL = "mongodb://test_url"
            mock_settings.MONGODB_DB_NAME = "test_db"

            await connect_to_mongo()

            mock_cls.assert_called_once_with("mongodb://test_url")

    @pytest.mark.asyncio
    async def test_realiza_ping_para_verificar_conexion(self):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock()

        with (
            patch("app.core.database.AsyncIOMotorClient", return_value=mock_client),
            patch("app.core.database.init_beanie", new_callable=AsyncMock),
            patch("app.core.database.settings") as mock_settings,
        ):
            mock_settings.MONGODB_URL = "mongodb://test_url"
            mock_settings.MONGODB_DB_NAME = "test_db"

            await connect_to_mongo()

            mock_client.admin.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_llama_init_beanie_con_modelos(self):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock()

        with (
            patch("app.core.database.AsyncIOMotorClient", return_value=mock_client),
            patch("app.core.database.init_beanie", new_callable=AsyncMock) as mock_beanie,
            patch("app.core.database.settings") as mock_settings,
        ):
            mock_settings.MONGODB_URL = "mongodb://test_url"
            mock_settings.MONGODB_DB_NAME = "test_db"

            await connect_to_mongo()

            mock_beanie.assert_called_once()
            call_kwargs = mock_beanie.call_args.kwargs
            assert "document_models" in call_kwargs
            assert len(call_kwargs["document_models"]) > 0

    @pytest.mark.asyncio
    async def test_propaga_excepcion_si_falla_conexion(self):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock(side_effect=Exception("Timeout"))

        with (
            patch("app.core.database.AsyncIOMotorClient", return_value=mock_client),
            patch("app.core.database.init_beanie", new_callable=AsyncMock),
            patch("app.core.database.settings") as mock_settings,
        ):
            mock_settings.MONGODB_URL = "mongodb://invalid"
            mock_settings.MONGODB_DB_NAME = "test_db"

            with pytest.raises(Exception, match="Timeout"):
                await connect_to_mongo()

    @pytest.mark.asyncio
    async def test_asigna_cliente_a_variable_global(self):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock()

        with (
            patch("app.core.database.AsyncIOMotorClient", return_value=mock_client),
            patch("app.core.database.init_beanie", new_callable=AsyncMock),
            patch("app.core.database.settings") as mock_settings,
        ):
            mock_settings.MONGODB_URL = "mongodb://test_url"
            mock_settings.MONGODB_DB_NAME = "test_db"

            await connect_to_mongo()

            assert db_module.mongodb_client is mock_client


class TestCloseMongoConnection:
    """Tests para close_mongo_connection."""

    @pytest.mark.asyncio
    async def test_llama_close_si_cliente_existe(self):
        mock_client = MagicMock()
        db_module.mongodb_client = mock_client

        await close_mongo_connection()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_falla_si_cliente_es_none(self):
        db_module.mongodb_client = None
        # No debe lanzar ninguna excepción
        await close_mongo_connection()

    @pytest.mark.asyncio
    async def test_cliente_sigue_siendo_el_mismo_objeto_tras_close(self):
        """close() cierra la conexión pero no pone el cliente en None."""
        mock_client = MagicMock()
        db_module.mongodb_client = mock_client

        await close_mongo_connection()

        mock_client.close.assert_called_once()
