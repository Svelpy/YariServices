"""
Tests de integración para auth routes.
Tipo: Integration — AuthService mockeado, exception_handlers registrado en setup.
Endpoints: POST /auth/register, POST /auth/login.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.shared.errors.exceptions import AppException
from app.domains.auth.routes import router
from app.middlewares.exception_handlers import register_exception_handlers


class TestAuthRoutesRegister:
    """Tests para POST /auth/register"""

    @pytest.fixture(autouse=True)
    def setup_app_client(self):
        self.app = FastAPI()
        self.app.include_router(router)
        register_exception_handlers(self.app)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        yield

    @patch("app.domains.auth.routes.AuthService.register_self")
    def test_registro_exitoso_retorna_201_con_usuario(self, mock_register_self):
        mock_register_self.return_value = {
            "id": "507f1f77bcf86cd799439011",
            "email": "maria@example.com",
            "name": "Maria",
            "lastname": "Garcia",
            "username": "mariag",
            "auth_provider": "LOCAL",
            "email_verified": False,
            "role": "USER",
            "status": "ACTIVE",
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
        }

        payload = {
            "email": "maria@example.com",
            "password": "Passw0rd123",
            "name": "Maria",
            "lastname": "Garcia",
            "username": "mariag",
        }

        response = self.client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["email"] == "maria@example.com"
        assert body["role"] == "USER"
        assert "password" not in body
        assert "password_hash" not in body
        mock_register_self.assert_called_once()

    @patch("app.domains.auth.routes.AuthService.register_self")
    def test_registro_solo_con_campos_requeridos_retorna_201(self, mock_register_self):
        """Campos opcionales (name, lastname, username) pueden omitirse."""
        mock_register_self.return_value = {
            "id": "507f1f77bcf86cd799439011",
            "email": "minimo@example.com",
            "auth_provider": "LOCAL",
            "email_verified": False,
            "role": "USER",
            "status": "ACTIVE",
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
        }

        payload = {
            "email": "minimo@example.com",
            "password": "Passw0rd123",
        }

        response = self.client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        mock_register_self.assert_called_once()

    @patch("app.domains.auth.routes.AuthService.register_self")
    def test_registro_sin_email_retorna_422(self, mock_register_self):
        payload = {"name": "Maria", "password": "Passw0rd123"}

        response = self.client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_register_self.assert_not_called()

    @patch("app.domains.auth.routes.AuthService.register_self")
    def test_registro_sin_password_retorna_422(self, mock_register_self):
        payload = {"email": "maria@example.com"}

        response = self.client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_register_self.assert_not_called()

    @patch("app.domains.auth.routes.AuthService.register_self")
    def test_registro_email_duplicado_retorna_409(self, mock_register_self):
        mock_register_self.side_effect = AppException("El email ya está registrado.", 409)

        payload = {
            "email": "repetido@example.com",
            "password": "Passw0rd123",
        }

        response = self.client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_409_CONFLICT
        body = response.json()
        assert body["status"] == "fail"
        assert "ya está registrado" in body["message"]

    @patch("app.domains.auth.routes.AuthService.register_self")
    def test_registro_username_duplicado_retorna_409(self, mock_register_self):
        mock_register_self.side_effect = AppException("El username ya está en uso.", 409)

        payload = {
            "email": "nuevo@example.com",
            "password": "Passw0rd123",
            "username": "repetido",
        }

        response = self.client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_409_CONFLICT
        body = response.json()
        assert body["status"] == "fail"
        assert "ya está en uso" in body["message"]


class TestAuthRoutesLogin:
    """Tests para POST /auth/login"""

    @pytest.fixture(autouse=True)
    def setup_app_client(self):
        self.app = FastAPI()
        self.app.include_router(router)
        register_exception_handlers(self.app)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        yield

    @patch("app.domains.auth.routes.AuthService.login")
    def test_login_exitoso_retorna_200_con_token(self, mock_login):
        mock_login.return_value = {
            "access_token": "token_jwt_valido",
            "token_type": "bearer",
        }

        payload = {
            "email": "usuario@example.com",
            "password": "Passw0rd123",
        }

        response = self.client.post("/auth/login", json=payload)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["access_token"] == "token_jwt_valido"
        assert body["token_type"] == "bearer"
        mock_login.assert_called_once()

    @patch("app.domains.auth.routes.AuthService.login")
    def test_login_sin_password_retorna_422(self, mock_login):
        payload = {"email": "usuario@example.com"}

        response = self.client.post("/auth/login", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_login.assert_not_called()

    @patch("app.domains.auth.routes.AuthService.login")
    def test_login_sin_email_retorna_422(self, mock_login):
        payload = {"password": "Passw0rd123"}

        response = self.client.post("/auth/login", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_login.assert_not_called()

    @patch("app.domains.auth.routes.AuthService.login")
    def test_login_credenciales_incorrectas_retorna_401(self, mock_login):
        mock_login.side_effect = AppException("Email o contraseña incorrectos.", 401)

        payload = {
            "email": "invalido@example.com",
            "password": "wrong_password",
        }

        response = self.client.post("/auth/login", json=payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        body = response.json()
        assert body["status"] == "fail"
        assert "incorrectos" in body["message"]

    @patch("app.domains.auth.routes.AuthService.login")
    def test_login_usuario_inactivo_retorna_403(self, mock_login):
        mock_login.side_effect = AppException("Usuario inactivo o no verificado.", 403)

        payload = {
            "email": "inactivo@example.com",
            "password": "Passw0rd123",
        }

        response = self.client.post("/auth/login", json=payload)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        body = response.json()
        assert body["status"] == "fail"
        assert "inactivo" in body["message"]
