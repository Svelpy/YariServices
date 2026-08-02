"""
Tests para register_cors.

Verifica que CORSMiddleware se registra en la app con los parámetros correctos
según el modo DEBUG (dev vs prod). CORSMiddleware en sí no se llama — solo
verificamos que add_middleware() recibe los argumentos esperados.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.middlewares.cors import register_cors


class TestRegisterCors:
    """Tests para register_cors."""

    def test_llama_add_middleware_con_cors_middleware(self):
        app = FastAPI()
        app.add_middleware = MagicMock()

        with patch("app.middlewares.cors.settings") as mock_settings:
            mock_settings.CORS_ORIGINS_LIST = ["http://localhost:5173"]
            register_cors(app)

        app.add_middleware.assert_called_once()
        args, kwargs = app.add_middleware.call_args
        assert args[0] is CORSMiddleware

    def test_origins_provienen_de_settings(self):
        app = FastAPI()
        app.add_middleware = MagicMock()
        expected_origins = ["http://localhost:5173", "http://localhost:5174"]

        with patch("app.middlewares.cors.settings") as mock_settings:
            mock_settings.CORS_ORIGINS_LIST = expected_origins
            register_cors(app)

        _, kwargs = app.add_middleware.call_args
        assert kwargs["allow_origins"] == expected_origins

    def test_allow_credentials_es_true(self):
        app = FastAPI()
        app.add_middleware = MagicMock()

        with patch("app.middlewares.cors.settings") as mock_settings:
            mock_settings.CORS_ORIGINS_LIST = ["http://localhost:5173"]
            register_cors(app)

        _, kwargs = app.add_middleware.call_args
        assert kwargs["allow_credentials"] is True

    def test_allow_methods_incluye_verbos_principales(self):
        app = FastAPI()
        app.add_middleware = MagicMock()

        with patch("app.middlewares.cors.settings") as mock_settings:
            mock_settings.CORS_ORIGINS_LIST = ["http://localhost:5173"]
            register_cors(app)

        _, kwargs = app.add_middleware.call_args
        methods = kwargs["allow_methods"]
        for verb in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
            assert verb in methods

    def test_allow_headers_incluye_authorization_y_content_type(self):
        app = FastAPI()
        app.add_middleware = MagicMock()

        with patch("app.middlewares.cors.settings") as mock_settings:
            mock_settings.CORS_ORIGINS_LIST = ["http://localhost:5173"]
            register_cors(app)

        _, kwargs = app.add_middleware.call_args
        headers = kwargs["allow_headers"]
        assert "Authorization" in headers
        assert "Content-Type" in headers

    def test_cors_funciona_en_app_real_dev(self):
        """Prueba de integración: respuesta CORS correcta en modo dev."""
        app = FastAPI()

        with patch("app.middlewares.cors.settings") as mock_settings:
            mock_settings.CORS_ORIGINS_LIST = ["http://localhost:5173"]
            register_cors(app)

        @app.get("/ping")
        def ping():
            return {"ok": True}

        client = TestClient(app)
        response = client.get(
            "/ping",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_rechaza_origen_no_permitido(self):
        """Origen no listado no recibe cabecera CORS."""
        app = FastAPI()

        with patch("app.middlewares.cors.settings") as mock_settings:
            mock_settings.CORS_ORIGINS_LIST = ["http://localhost:5173"]
            register_cors(app)

        @app.get("/ping")
        def ping():
            return {"ok": True}

        client = TestClient(app)
        response = client.get(
            "/ping",
            headers={"Origin": "http://evil.com"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") != "http://evil.com"
