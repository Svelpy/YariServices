"""
Tests unitarios para AuthService.
Tipo: Unit — BD (User), tokens y hashes están mockeados.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException
from app.domains.auth import AuthService, UserLogin, UserSelfRegister


class TestAuthServiceRegisterSelf:
    """Tests para AuthService.register_self"""

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.hash_password")
    async def test_registro_exitoso_con_username(self, mock_hash, mock_user_cls):
        user_data = UserSelfRegister(
            email="nuevo@example.com",
            name="Juan",
            lastname="Perez",
            username="juanp",
            password="Password123",
            phone_number="+59170011223",
        )

        mock_hash.return_value = "hashed_pass"
        mock_user_cls.find_one = AsyncMock(return_value=None)

        mock_user_instance = MagicMock()
        mock_user_instance.save = AsyncMock()
        mock_user_cls.return_value = mock_user_instance

        result = await AuthService.register_self(user_data)

        assert result is mock_user_instance
        mock_hash.assert_called_once_with("Password123")
        mock_user_instance.save.assert_called_once()
        # Se verifican email y username en BD
        assert mock_user_cls.find_one.call_count == 2

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.hash_password")
    async def test_registro_exitoso_sin_username(self, mock_hash, mock_user_cls):
        """Sin username, solo se verifica el email en BD."""
        user_data = UserSelfRegister(
            email="nuevo@example.com",
            password="Password123",
        )

        mock_hash.return_value = "hashed_pass"
        mock_user_cls.find_one = AsyncMock(return_value=None)

        mock_user_instance = MagicMock()
        mock_user_instance.save = AsyncMock()
        mock_user_cls.return_value = mock_user_instance

        result = await AuthService.register_self(user_data)

        assert result is mock_user_instance
        # Solo se consulta email, no username
        mock_user_cls.find_one.assert_called_once()
        mock_user_instance.save.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.hash_password")
    async def test_registro_username_con_mayusculas_se_normaliza(
        self, mock_hash, mock_user_cls
    ):
        """El username se normaliza con strip().lower() antes de guardarse."""
        user_data = UserSelfRegister(
            email="nuevo@example.com",
            username="JuanP",
            password="Password123",
        )

        mock_hash.return_value = "hashed_pass"
        mock_user_cls.find_one = AsyncMock(return_value=None)

        mock_user_instance = MagicMock()
        mock_user_instance.save = AsyncMock()
        mock_user_cls.return_value = mock_user_instance

        await AuthService.register_self(user_data)

        call_kwargs = mock_user_cls.call_args.kwargs
        assert call_kwargs["username"] == "juanp"

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    async def test_registro_email_duplicado_lanza_409(self, mock_user_cls):
        user_data = UserSelfRegister(
            email="repetido@example.com",
            password="Password123",
        )
        mock_user_cls.find_one = AsyncMock(return_value=MagicMock())

        with pytest.raises(AppException) as exc_info:
            await AuthService.register_self(user_data)

        assert exc_info.value.status_code == 409
        assert "email ya está registrado" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    async def test_registro_username_duplicado_lanza_409(self, mock_user_cls):
        user_data = UserSelfRegister(
            email="nuevo@example.com",
            username="repetido",
            password="Password123",
        )

        # Primera llamada (email) -> None, segunda (username) -> usuario existente
        mock_user_cls.find_one = AsyncMock(side_effect=[None, MagicMock()])

        with pytest.raises(AppException) as exc_info:
            await AuthService.register_self(user_data)

        assert exc_info.value.status_code == 409
        assert "username ya está en uso" in exc_info.value.message


class TestAuthServiceLogin:
    """Tests para AuthService.login"""

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.verify_password")
    @patch("app.domains.auth.services.create_access_token")
    async def test_login_exitoso_retorna_token_response(
        self, mock_create_token, mock_verify, mock_user_cls
    ):
        credentials = UserLogin(email="user@example.com", password="Password123")

        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.email = "user@example.com"
        mock_user.password_hash = "hashed_pass"
        mock_user.status = UserStatus.ACTIVE
        mock_user.role = Role.USER
        mock_user.is_deleted = False

        mock_user_cls.find_one = AsyncMock(return_value=mock_user)
        mock_verify.return_value = True
        mock_create_token.return_value = "fake_jwt_token"

        result = await AuthService.login(credentials)

        assert result.access_token == "fake_jwt_token"
        assert result.token_type == "bearer"
        mock_verify.assert_called_once_with("Password123", "hashed_pass")

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.verify_password")
    @patch("app.domains.auth.services.create_access_token")
    async def test_login_exitoso_payload_contiene_user_id_email_role(
        self, mock_create_token, mock_verify, mock_user_cls
    ):
        """El payload enviado a create_access_token incluye user_id, email y role."""
        credentials = UserLogin(email="user@example.com", password="Password123")

        mock_user = MagicMock()
        mock_user.id = "507f1f77bcf86cd799439011"
        mock_user.email = "user@example.com"
        mock_user.password_hash = "hashed_pass"
        mock_user.status = UserStatus.ACTIVE
        mock_user.role = Role.USER

        mock_user_cls.find_one = AsyncMock(return_value=mock_user)
        mock_verify.return_value = True
        mock_create_token.return_value = "fake_jwt_token"

        await AuthService.login(credentials)

        mock_create_token.assert_called_once()
        payload = mock_create_token.call_args.kwargs.get("data") or mock_create_token.call_args.args[0]
        assert "user_id" in payload
        assert payload["email"] == "user@example.com"
        assert "role" in payload

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    async def test_login_usuario_no_existe_lanza_401(self, mock_user_cls):
        credentials = UserLogin(email="noexiste@example.com", password="Password123")
        mock_user_cls.find_one = AsyncMock(return_value=None)

        with pytest.raises(AppException) as exc_info:
            await AuthService.login(credentials)

        assert exc_info.value.status_code == 401
        assert "incorrectos" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.verify_password")
    async def test_login_contrasena_incorrecta_lanza_401(self, mock_verify, mock_user_cls):
        credentials = UserLogin(email="user@example.com", password="wrong_pass")

        mock_user = MagicMock()
        mock_user.password_hash = "hashed_pass"
        mock_user_cls.find_one = AsyncMock(return_value=mock_user)
        mock_verify.return_value = False

        with pytest.raises(AppException) as exc_info:
            await AuthService.login(credentials)

        assert exc_info.value.status_code == 401
        assert "incorrectos" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    async def test_login_usuario_sin_password_hash_lanza_401(self, mock_user_cls):
        """Usuario sin password_hash (p.ej. OAuth) no puede hacer login local."""
        credentials = UserLogin(email="oauth@example.com", password="Password123")

        mock_user = MagicMock()
        mock_user.password_hash = None
        mock_user_cls.find_one = AsyncMock(return_value=mock_user)

        with pytest.raises(AppException) as exc_info:
            await AuthService.login(credentials)

        assert exc_info.value.status_code == 401
        assert "incorrectos" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.verify_password")
    async def test_login_usuario_inactivo_lanza_403(self, mock_verify, mock_user_cls):
        credentials = UserLogin(email="user@example.com", password="Password123")

        mock_user = MagicMock()
        mock_user.password_hash = "hashed_pass"
        mock_user.status = UserStatus.INACTIVE
        mock_user_cls.find_one = AsyncMock(return_value=mock_user)
        mock_verify.return_value = True

        with pytest.raises(AppException) as exc_info:
            await AuthService.login(credentials)

        assert exc_info.value.status_code == 403
        assert "inactivo" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.auth.services.User")
    @patch("app.domains.auth.services.verify_password")
    async def test_login_usuario_suspendido_lanza_403(self, mock_verify, mock_user_cls):
        credentials = UserLogin(email="user@example.com", password="Password123")

        mock_user = MagicMock()
        mock_user.password_hash = "hashed_pass"
        mock_user.status = UserStatus.SUSPENDED
        mock_user_cls.find_one = AsyncMock(return_value=mock_user)
        mock_verify.return_value = True

        with pytest.raises(AppException) as exc_info:
            await AuthService.login(credentials)

        assert exc_info.value.status_code == 403
        assert "inactivo" in exc_info.value.message
