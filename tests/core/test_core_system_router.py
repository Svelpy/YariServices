from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.core.database as db_module
from app.core.system_router import router


@pytest.fixture()
def app_client():
    """Crea una app FastAPI mínima con el system_router montado."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, follow_redirects=False)


class TestRootEndpoint:
    """Tests para GET /"""

    def test_debug_true_redirige_a_docs(self, app_client):
        with patch("app.core.system_router.settings") as mock_settings:
            mock_settings.DEBUG = True
            response = app_client.get("/")
        assert response.status_code == 307
        assert response.headers["location"] == "/docs"

    def test_debug_false_devuelve_json(self, app_client):
        with patch("app.core.system_router.settings") as mock_settings:
            mock_settings.DEBUG = False
            response = app_client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Svelpy API"
        assert body["status"] == "active"


class TestHealthEndpoint:
    """Tests para GET /health"""

    def test_db_conectada_devuelve_200_healthy(self, app_client):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        db_module.mongodb_client = mock_client

        with patch("app.core.system_router.settings") as mock_settings:
            mock_settings.APP_NAME = "TestApp"
            mock_settings.APP_VERSION = "1.0.0"
            response = app_client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["database"] == "connected"

        db_module.mongodb_client = None

    def test_db_desconectada_cliente_none_devuelve_503(self, app_client):
        db_module.mongodb_client = None

        with patch("app.core.system_router.settings") as mock_settings:
            mock_settings.APP_NAME = "TestApp"
            mock_settings.APP_VERSION = "1.0.0"
            response = app_client.get("/health")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "error"
        assert body["details"]["database"] == "disconnected"

    def test_db_lanza_excepcion_devuelve_503(self, app_client):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock(side_effect=Exception("DB timeout"))
        db_module.mongodb_client = mock_client

        with patch("app.core.system_router.settings") as mock_settings:
            mock_settings.APP_NAME = "TestApp"
            mock_settings.APP_VERSION = "1.0.0"
            response = app_client.get("/health")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "error"
        assert "DB timeout" in body["details"]["reason"]

        db_module.mongodb_client = None

    def test_health_incluye_app_name_y_version(self, app_client):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        db_module.mongodb_client = mock_client

        with patch("app.core.system_router.settings") as mock_settings:
            mock_settings.APP_NAME = "MiApp"
            mock_settings.APP_VERSION = "2.5.0"
            response = app_client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["app"] == "MiApp"
        assert body["version"] == "2.5.0"

        db_module.mongodb_client = None
