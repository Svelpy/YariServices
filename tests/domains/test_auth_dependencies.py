"""
Tests unitarios para las dependencias de auth (FastAPI guards).
Tipo: Unit — decode_access_token y User.get están mockeados.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from beanie import PydanticObjectId

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.shared.enums import Action, Module, Role, UserStatus
from app.domains.auth import (
    resolve_authorized_business_id,
    get_current_user,
    get_current_user_optional,
    require_permission,
    require_roles,
)


class TestGetCurrentUser:
    """Tests para get_current_user"""

    @pytest.mark.asyncio
    async def test_credenciales_none_lanza_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token de autenticación requerido" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.decode_access_token")
    async def test_token_invalido_retorna_none_del_decode_lanza_401(self, mock_decode):
        mock_decode.return_value = None
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_invalido")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token inválido" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.decode_access_token")
    async def test_token_sin_user_id_en_payload_lanza_401(self, mock_decode):
        mock_decode.return_value = {"email": "sin_user_id@example.com"}
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_valido")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token inválido" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.User")
    @patch("app.domains.auth.dependencies.decode_access_token")
    async def test_user_get_retorna_none_lanza_401(self, mock_decode, mock_user_cls):
        mock_decode.return_value = {"user_id": "507f1f77bcf86cd799439011"}
        mock_user_cls.get = AsyncMock(return_value=None)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_valido")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Usuario no encontrado" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.User")
    @patch("app.domains.auth.dependencies.decode_access_token")
    async def test_user_eliminado_lanza_401(self, mock_decode, mock_user_cls):
        mock_user = MagicMock()
        mock_user.is_deleted = True
        mock_decode.return_value = {"user_id": "507f1f77bcf86cd799439011"}
        mock_user_cls.get = AsyncMock(return_value=mock_user)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_valido")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Usuario no encontrado" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.User")
    @patch("app.domains.auth.dependencies.decode_access_token")
    async def test_user_inactivo_lanza_403(self, mock_decode, mock_user_cls):
        mock_user = MagicMock()
        mock_user.is_deleted = False
        mock_user.status = UserStatus.PENDING_VERIFICATION
        mock_decode.return_value = {"user_id": "507f1f77bcf86cd799439011"}
        mock_user_cls.get = AsyncMock(return_value=mock_user)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_valido")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Usuario inactivo o no verificado" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.User")
    @patch("app.domains.auth.dependencies.decode_access_token")
    async def test_user_valido_retorna_usuario(self, mock_decode, mock_user_cls):
        mock_user = MagicMock()
        mock_user.is_deleted = False
        mock_user.status = UserStatus.ACTIVE
        mock_decode.return_value = {"user_id": "507f1f77bcf86cd799439011"}
        mock_user_cls.get = AsyncMock(return_value=mock_user)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_valido")

        result = await get_current_user(credentials=creds)
        assert result is mock_user


class TestRequireRoles:
    """Tests para require_roles"""

    @pytest.mark.asyncio
    async def test_role_permitido_retorna_usuario(self):
        mock_user = MagicMock()
        mock_user.role = Role.ADMIN
        guard = require_roles(Role.ADMIN, Role.SUPERADMIN)
        result = await guard(current_user=mock_user)
        assert result is mock_user

    @pytest.mark.asyncio
    async def test_role_no_permitido_lanza_403(self):
        mock_user = MagicMock()
        mock_user.role = Role.VENDEDOR
        guard = require_roles(Role.ADMIN, Role.SUPERADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await guard(current_user=mock_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestRequirePermission:
    """Tests para require_permission"""

    @pytest.mark.asyncio
    async def test_permiso_concedido_retorna_usuario(self):
        mock_user = MagicMock()
        mock_user.role = Role.PROPIETARIO
        guard = require_permission(Module.CATEGORY, Action.CREATE)
        result = await guard(current_user=mock_user)
        assert result is mock_user

    @pytest.mark.asyncio
    async def test_permiso_denegado_lanza_403(self):
        mock_user = MagicMock()
        mock_user.role = Role.VENDEDOR
        guard = require_permission(Module.CATEGORY, Action.DELETE)
        with pytest.raises(HTTPException) as exc_info:
            await guard(current_user=mock_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestGetCurrentBusinessId:
    """Tests para resolve_authorized_business_id"""

    @pytest.mark.asyncio
    async def test_usuario_negocio_retorna_su_business_id(self):
        mock_user = MagicMock()
        mock_user.role = Role.PROPIETARIO
        bid = PydanticObjectId()
        mock_user.business_id = bid

        result = await resolve_authorized_business_id(business_id=None, current_user=mock_user)
        assert result == bid

    @pytest.mark.asyncio
    async def test_admin_sin_business_id_lanza_400(self):
        mock_user = MagicMock()
        mock_user.role = Role.ADMIN

        with pytest.raises(HTTPException) as exc_info:
            await resolve_authorized_business_id(business_id=None, current_user=mock_user)
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_admin_con_business_id_retorna_business_id(self):
        mock_user = MagicMock()
        mock_user.role = Role.ADMIN
        bid = PydanticObjectId()

        result = await resolve_authorized_business_id(business_id=bid, current_user=mock_user)
        assert result == bid


class TestGetCurrentUserOptional:
    """Tests para get_current_user_optional"""

    @pytest.mark.asyncio
    async def test_sin_credenciales_retorna_none(self):
        result = await get_current_user_optional(credentials=None)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.domains.auth.dependencies.get_current_user")
    async def test_credenciales_validas_retorna_usuario(self, mock_get_user):
        mock_user = MagicMock()
        mock_get_user.return_value = mock_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_valido")

        result = await get_current_user_optional(credentials=creds)

        assert result is mock_user
