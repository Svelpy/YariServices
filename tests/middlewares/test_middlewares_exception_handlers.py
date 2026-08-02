"""
Tests para register_exception_handlers.

Cubre los cuatro handlers registrados:
  - AppException       → status_code propio, body con "fail"
  - RequestValidationError → 422, details con campos y mensajes
  - StarletteHTTPException → status_code propio, body con "fail"
  - Exception genérica (DEBUG=True)  → 500 con stack trace
  - Exception genérica (DEBUG=False) → 500 genérico + intento de log en MongoDB (mockeado)
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middlewares.exception_handlers import register_exception_handlers
from app.shared.errors.exceptions import AppException


# ---------------------------------------------------------------------------
# Fixture: app con los handlers registrados
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_with_handlers():
    """App mínima con los exception handlers registrados y rutas de prueba."""
    app = FastAPI()
    register_exception_handlers(app)

    # Ruta que lanza AppException
    @app.get("/app-error")
    def raise_app_error():
        raise AppException("recurso no encontrado", status_code=404)

    # Ruta que lanza AppException con 400
    @app.get("/app-error-400")
    def raise_app_error_400():
        raise AppException("solicitud inválida", status_code=400)

    # Ruta que lanza HTTPException de Starlette
    @app.get("/http-error")
    def raise_http_error():
        raise StarletteHTTPException(status_code=403, detail="Acceso denegado")

    # Ruta que lanza excepción genérica
    @app.get("/server-error")
    def raise_server_error():
        raise RuntimeError("Error interno inesperado")

    # Ruta con validación Pydantic (query param obligatorio)
    @app.get("/validated")
    def validated_route(name: str):
        return {"name": name}

    return app


# ---------------------------------------------------------------------------
# AppException handler
# ---------------------------------------------------------------------------

class TestAppExceptionHandler:
    """Tests para el handler de AppException."""

    def test_status_code_correcto(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        response = client.get("/app-error")
        assert response.status_code == 404

    def test_body_status_fail(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/app-error").json()
        assert body["status"] == "fail"

    def test_body_contiene_mensaje(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/app-error").json()
        assert body["message"] == "recurso no encontrado"

    def test_body_details_es_dict_vacio(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/app-error").json()
        assert body["details"] == {}

    def test_status_code_400(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        response = client.get("/app-error-400")
        assert response.status_code == 400
        assert client.get("/app-error-400").json()["message"] == "solicitud inválida"


# ---------------------------------------------------------------------------
# RequestValidationError handler
# ---------------------------------------------------------------------------

class TestValidationExceptionHandler:
    """Tests para el handler de RequestValidationError."""

    def test_status_code_422(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        # Llamar sin el query param obligatorio 'name'
        response = client.get("/validated")
        assert response.status_code == 422

    def test_body_status_fail(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/validated").json()
        assert body["status"] == "fail"

    def test_body_mensaje_datos_invalidos(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/validated").json()
        assert "válidos" in body["message"] or "válido" in body["message"]

    def test_body_details_contiene_errores(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/validated").json()
        assert isinstance(body["details"], dict)
        assert len(body["details"]) > 0


# ---------------------------------------------------------------------------
# StarletteHTTPException handler
# ---------------------------------------------------------------------------

class TestHttpExceptionHandler:
    """Tests para el handler de StarletteHTTPException."""

    def test_status_code_correcto(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        response = client.get("/http-error")
        assert response.status_code == 403

    def test_body_status_fail(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/http-error").json()
        assert body["status"] == "fail"

    def test_body_contiene_detail(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/http-error").json()
        assert body["message"] == "Acceso denegado"

    def test_body_details_es_dict_vacio(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        body = client.get("/http-error").json()
        assert body["details"] == {}


# ---------------------------------------------------------------------------
# Exception genérica — DEBUG=True
# ---------------------------------------------------------------------------

class TestGlobalExceptionHandlerDebugTrue:
    """Handler de Exception con DEBUG=True: expone stack trace."""

    def test_status_code_500(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with patch("app.middlewares.exception_handlers.settings") as mock_s:
            mock_s.DEBUG = True
            response = client.get("/server-error")
        assert response.status_code == 500

    def test_body_status_error(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with patch("app.middlewares.exception_handlers.settings") as mock_s:
            mock_s.DEBUG = True
            body = client.get("/server-error").json()
        assert body["status"] == "error"

    def test_body_message_contiene_excepcion(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with patch("app.middlewares.exception_handlers.settings") as mock_s:
            mock_s.DEBUG = True
            body = client.get("/server-error").json()
        assert "Error interno inesperado" in body["message"]

    def test_body_details_contiene_stack(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with patch("app.middlewares.exception_handlers.settings") as mock_s:
            mock_s.DEBUG = True
            body = client.get("/server-error").json()
        assert "stack" in body["details"]
        assert len(body["details"]["stack"]) > 0


# ---------------------------------------------------------------------------
# Exception genérica — DEBUG=False
# ---------------------------------------------------------------------------

class TestGlobalExceptionHandlerDebugFalse:
    """Handler de Exception con DEBUG=False: mensaje genérico + intento de log en DB."""

    def test_status_code_500(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with (
            patch("app.middlewares.exception_handlers.settings") as mock_s,
            patch("app.middlewares.exception_handlers.ErrorLog") as mock_log_cls,
        ):
            mock_s.DEBUG = False
            mock_instance = AsyncMock()
            mock_log_cls.return_value = mock_instance
            response = client.get("/server-error")
        assert response.status_code == 500

    def test_body_mensaje_generico(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with (
            patch("app.middlewares.exception_handlers.settings") as mock_s,
            patch("app.middlewares.exception_handlers.ErrorLog") as mock_log_cls,
        ):
            mock_s.DEBUG = False
            mock_instance = AsyncMock()
            mock_log_cls.return_value = mock_instance
            body = client.get("/server-error").json()
        assert body["status"] == "error"
        assert "Miechi" in body["message"] or "mal" in body["message"]

    def test_body_no_expone_stack(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with (
            patch("app.middlewares.exception_handlers.settings") as mock_s,
            patch("app.middlewares.exception_handlers.ErrorLog") as mock_log_cls,
        ):
            mock_s.DEBUG = False
            mock_instance = AsyncMock()
            mock_log_cls.return_value = mock_instance
            body = client.get("/server-error").json()
        assert body.get("details") == {}

    def test_body_details_vacio_sin_stack(self, app_with_handlers):
        client = TestClient(app_with_handlers, raise_server_exceptions=False)
        with (
            patch("app.middlewares.exception_handlers.settings") as mock_s,
            patch("app.middlewares.exception_handlers.ErrorLog") as mock_log_cls,
        ):
            mock_s.DEBUG = False
            mock_instance = AsyncMock()
            mock_log_cls.return_value = mock_instance
            body = client.get("/server-error").json()
        assert "stack" not in body.get("details", {})
