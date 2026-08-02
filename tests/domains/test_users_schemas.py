"""
Tests unitarios para los esquemas Pydantic del dominio users.
Tipo: Unit — Validación de entrada y serialización de salida.
"""
from datetime import datetime
import pytest
from pydantic import ValidationError

from app.shared.enums import Role, UserStatus
from app.domains.users import (
    AdminResetPassword,
    PasswordSelfUpdate,
    UserCreate,
    UserSelfRegister,
    UserSelfUpdate,
    UserUpdate,
)


class TestUserSelfRegisterSchema:
    """Tests de validación para UserSelfRegister."""

    def test_schema_valido(self):
        data = {
            "email": "test@example.com",
            "name": "Carlos",
            "lastname": "Gomez",
            "username": "carlosg",
            "phone_number": "+59170011223",
            "birth_date": datetime(1995, 5, 15),
            "password": "Password123",
        }
        schema = UserSelfRegister(**data)
        assert schema.email == "test@example.com"
        assert schema.name == "Carlos"
        assert schema.username == "carlosg"

    def test_password_demasiado_corto_lanza_error(self):
        with pytest.raises(ValidationError) as exc_info:
            UserSelfRegister(email="test@example.com", password="123")
        assert "password" in str(exc_info.value)

    def test_nombre_invalido_lanza_error(self):
        with pytest.raises(ValidationError) as exc_info:
            UserSelfRegister(
                email="test@example.com",
                name="Carlos123",
                password="Password123"
            )
        assert "name" in str(exc_info.value)


class TestUserCreateSchema:
    """Tests de validación para UserCreate."""

    def test_user_create_valido(self):
        data = {
            "email": "admin@example.com",
            "password": "Password123",
            "role": Role.ADMIN,
        }
        schema = UserCreate(**data)
        assert schema.role == Role.ADMIN

    def test_role_default_es_user(self):
        schema = UserCreate(email="user@example.com", password="Password123")
        assert schema.role == Role.USER


class TestUserSelfUpdateSchema:
    """Tests de validación para UserSelfUpdate."""

    def test_self_update_campos_opcionales(self):
        schema = UserSelfUpdate(name="Carlos")
        assert schema.name == "Carlos"
        assert schema.lastname is None
        assert schema.username is None

    def test_username_invalido_lanza_error(self):
        with pytest.raises(ValidationError) as exc_info:
            UserSelfUpdate(username="user_invalid@")
        assert "username" in str(exc_info.value)


class TestUserUpdateSchema:
    """Tests de validación para UserUpdate."""

    def test_update_permite_campos_administrativos(self):
        schema = UserUpdate(
            email="nuevo@example.com",
            role=Role.GERENTE,
            status=UserStatus.SUSPENDED
        )
        assert schema.email == "nuevo@example.com"
        assert schema.role == Role.GERENTE
        assert schema.status == UserStatus.SUSPENDED


class TestAdminResetPasswordSchema:
    """Tests de validación para AdminResetPassword."""

    def test_reset_valido(self):
        schema = AdminResetPassword(new_password="NuevaContrasena123")
        assert schema.new_password == "NuevaContrasena123"

    def test_reset_corto_lanza_error(self):
        with pytest.raises(ValidationError):
            AdminResetPassword(new_password="short")


class TestPasswordSelfUpdateSchema:
    """Tests de validación para PasswordSelfUpdate."""

    def test_change_valido(self):
        schema = PasswordSelfUpdate(
            current_password="ViejaContrasena123",
            new_password="NuevaContrasena123"
        )
        assert schema.current_password == "ViejaContrasena123"
        assert schema.new_password == "NuevaContrasena123"
