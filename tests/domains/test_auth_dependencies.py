from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.auth.dependencies import (
    _get_token_claims,
    get_current_user,
    require_permission,
    require_roles,
    resolve_authorized_business_id,
)
from app.domains.auth.schemas import TokenClaims
from app.shared.enums import Action, Module, Role
from app.shared.errors.codes import ErrorCode
from app.shared.errors.exceptions import AppException


def test_missing_token_has_stable_error_code(test_settings):
    with pytest.raises(AppException) as error:
        _get_token_claims(None, test_settings)

    assert error.value.status_code == 401
    assert error.value.code == ErrorCode.TOKEN_REQUIRED


def test_invalid_token_has_stable_error_code(test_settings):
    with patch("app.domains.auth.dependencies.decode_access_token", return_value=None):
        with pytest.raises(AppException) as error:
            _get_token_claims("invalid", test_settings)

    assert error.value.status_code == 401
    assert error.value.code == ErrorCode.TOKEN_INVALID


@pytest.mark.asyncio
async def test_current_user_rejects_unknown_user(test_settings):
    claims = TokenClaims(
        sub="507f1f77bcf86cd799439011",
        role=Role.ADMIN,
        iat=datetime.now(timezone.utc),
        exp=datetime.now(timezone.utc),
        jti="jti",
    )

    with (
        patch("app.domains.auth.dependencies._get_token_claims", return_value=claims),
        patch("app.domains.auth.dependencies.User") as user_model,
    ):
        user_model.get = AsyncMock(return_value=None)

        with pytest.raises(AppException) as error:
            await get_current_user("access", test_settings)

    assert error.value.status_code == 401
    assert error.value.code == ErrorCode.TOKEN_INVALID


@pytest.mark.asyncio
async def test_require_roles_rejects_forbidden_role():
    current_user = SimpleNamespace(role=Role.VENDEDOR)
    dependency = require_roles(Role.ADMIN, Role.SUPERADMIN)

    with pytest.raises(AppException) as error:
        await dependency(current_user)

    assert error.value.status_code == 403
    assert error.value.code == ErrorCode.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_require_permission_rejects_forbidden_action():
    current_user = SimpleNamespace(role=Role.VENDEDOR)
    dependency = require_permission(Module.CATEGORY, Action.DELETE)

    with pytest.raises(AppException) as error:
        await dependency(current_user)

    assert error.value.status_code == 403
    assert error.value.code == ErrorCode.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_business_user_uses_own_tenant():
    business_id = "507f1f77bcf86cd799439011"
    current_user = SimpleNamespace(role=Role.PROPIETARIO, business_id=business_id)

    result = await resolve_authorized_business_id(None, current_user)

    assert result == business_id


@pytest.mark.asyncio
async def test_platform_user_requires_target_tenant():
    current_user = SimpleNamespace(role=Role.ADMIN, business_id=None)

    with pytest.raises(AppException) as error:
        await resolve_authorized_business_id(None, current_user)

    assert error.value.status_code == 400
    assert error.value.code == ErrorCode.VALIDATION_ERROR
