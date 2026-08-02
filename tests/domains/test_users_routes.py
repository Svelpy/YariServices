"""
Tests de integración para las rutas del dominio users.
Tipo: Integration — UserService y dependencias de auth mockeados.
Endpoints: GET/POST/PATCH/DELETE /users, /users/me, etc.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from beanie import PydanticObjectId
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.shared.enums import Role, UserStatus, AuthProvider
from app.domains.auth.dependencies import get_current_business_id, get_current_user
from app.domains.users import User
from app.domains.users.routes import router
from app.middlewares.exception_handlers import register_exception_handlers


class TestUsersRoutes:
    """Suite de tests para las rutas de users."""

    @pytest.fixture(autouse=True)
    def setup_app_client(self):
        self.app = FastAPI()
        self.app.include_router(router)
        register_exception_handlers(self.app)
        self.client = TestClient(self.app, raise_server_exceptions=False)

        self.mock_admin = User.model_construct(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            email="admin@example.com",
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True,
            auth_provider=AuthProvider.LOCAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_deleted=False
        )

        self.mock_user = User.model_construct(
            id=PydanticObjectId("507f1f77bcf86cd799439022"),
            email="yo@example.com",
            role=Role.USER,
            status=UserStatus.ACTIVE,
            email_verified=True,
            auth_provider=AuthProvider.LOCAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_deleted=False
        )

        self.fake_bid = PydanticObjectId("507f1f77bcf86cd799439099")

        yield
        self.app.dependency_overrides.clear()

    @patch("app.domains.users.routes.UserService.register_user")
    def test_create_user_exitoso(self, mock_register):
        # Sobreescribir get_current_user (dependencia raíz) en lugar de require_permission
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_admin
        self.app.dependency_overrides[get_current_business_id] = lambda: self.fake_bid

        mock_user_resp = {
            "id": "507f1f77bcf86cd799439033",
            "email": "creado@example.com",
            "role": "GERENTE",
            "status": "ACTIVE",
            "email_verified": False,
            "auth_provider": "LOCAL",
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
            "is_deleted": False,
        }
        mock_register.return_value = mock_user_resp

        payload = {
            "email": "creado@example.com",
            "password": "Password123",
            "role": "GERENTE",
        }

        response = self.client.post("/users", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["email"] == "creado@example.com"
        assert body["role"] == "GERENTE"
        mock_register.assert_called_once()

    @patch("app.domains.users.routes.UserService.list_users")
    def test_list_users_exitoso(self, mock_list):
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_admin
        self.app.dependency_overrides[get_current_business_id] = lambda: self.fake_bid

        mock_list.return_value = {
            "total": 1,
            "page": 1,
            "per_page": 10,
            "total_pages": 1,
            "data": [
                {
                    "id": "507f1f77bcf86cd799439033",
                    "email": "user1@example.com",
                    "role": "USER",
                    "status": "ACTIVE",
                    "email_verified": True,
                    "auth_provider": "LOCAL",
                    "created_at": "2026-08-01T00:00:00Z",
                    "updated_at": "2026-08-01T00:00:00Z",
                    "is_deleted": False,
                }
            ],
        }

        response = self.client.get("/users")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["email"] == "user1@example.com"
        mock_list.assert_called_once()

    def test_get_me_retorna_usuario_autenticado(self):
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_user

        response = self.client.get("/users/me")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["email"] == "yo@example.com"

    @patch("app.domains.users.routes.UserService.get_user")
    def test_get_user_by_id_exitoso(self, mock_get_user):
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_admin

        user_id = "507f1f77bcf86cd799439033"
        mock_get_user.return_value = {
            "id": user_id,
            "email": "target@example.com",
            "role": "USER",
            "status": "ACTIVE",
            "email_verified": True,
            "auth_provider": "LOCAL",
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
            "is_deleted": False,
        }

        response = self.client.get(f"/users/{user_id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["email"] == "target@example.com"
        mock_get_user.assert_called_once()

    @patch("app.domains.users.routes.UserService.update_profile")
    def test_update_profile_exitoso(self, mock_update_profile):
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_user

        mock_updated = {
            "id": "507f1f77bcf86cd799439022",
            "email": "yo@example.com",
            "name": "Pedro",
            "lastname": "Perez",
            "username": "pedrop",
            "role": "USER",
            "status": "ACTIVE",
            "email_verified": True,
            "auth_provider": "LOCAL",
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
        }
        mock_update_profile.return_value = mock_updated

        payload = {"name": "Pedro", "lastname": "Perez"}

        response = self.client.patch("/users/me", json=payload)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["name"] == "Pedro"
        mock_update_profile.assert_called_once()

    @patch("app.domains.users.routes.UserService.update_user")
    def test_update_user_exitoso(self, mock_update_user):
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_admin

        user_id = "507f1f77bcf86cd799439033"
        mock_update_user.return_value = {
            "id": user_id,
            "email": "actualizado@example.com",
            "name": "Juan",
            "role": "GERENTE",
            "status": "ACTIVE",
            "email_verified": True,
            "auth_provider": "LOCAL",
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
            "is_deleted": False,
        }

        payload = {"name": "Juan"}

        response = self.client.patch(f"/users/{user_id}", json=payload)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Juan"
        mock_update_user.assert_called_once()

    @patch("app.domains.users.routes.UserService.change_password")
    def test_change_password_exitoso(self, mock_change):
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_user
        mock_change.return_value = None

        payload = {
            "current_password": "OldPassword123",
            "new_password": "NewPassword123",
        }

        response = self.client.post("/users/me/password", json=payload)

        assert response.status_code == status.HTTP_200_OK
        mock_change.assert_called_once()

    @patch("app.domains.users.routes.UserService.reset_password")
    def test_reset_password_exitoso(self, mock_reset):
        self.app.dependency_overrides[get_current_user] = lambda: self.mock_admin
        mock_reset.return_value = None

        user_id = "507f1f77bcf86cd799439033"
        payload = {"new_password": "NewPassword123"}

        response = self.client.post(f"/users/{user_id}/password", json=payload)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["detail"] == "Contraseña restablecida exitosamente"
        mock_reset.assert_called_once()

    @patch("app.domains.users.routes.UserService.delete_user")
    def test_delete_user_exitoso(self, mock_delete):
        # DELETE en USERS requiere SUPERADMIN o PROPIETARIO (ADMIN tiene SIN_ELIMINAR)
        mock_superadmin = User.model_construct(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            email="superadmin@example.com",
            role=Role.SUPERADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True,
            auth_provider=AuthProvider.LOCAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_deleted=False
        )
        self.app.dependency_overrides[get_current_user] = lambda: mock_superadmin
        mock_delete.return_value = None

        user_id = "507f1f77bcf86cd799439033"
        response = self.client.delete(f"/users/{user_id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["detail"] == "Usuario eliminado exitosamente"
        mock_delete.assert_called_once()
