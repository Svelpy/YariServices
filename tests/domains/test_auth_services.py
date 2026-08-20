from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.auth.schemas import UserLogin
from app.domains.auth.services import AuthService
from app.shared.enums import Role, UserStatus
from app.shared.errors.codes import ErrorCode
from app.shared.errors.exceptions import AppException


@pytest.mark.asyncio
async def test_validate_user_access_rejects_deleted_user(test_settings):
    user = SimpleNamespace(is_deleted=True)

    with pytest.raises(AppException) as error:
        await AuthService.validate_user_access(user)

    assert error.value.status_code == 401
    assert error.value.code == ErrorCode.AUTHENTICATION_FAILED


@pytest.mark.asyncio
async def test_validate_user_access_rejects_inactive_user(test_settings):
    user = SimpleNamespace(
        is_deleted=False,
        status=UserStatus.INACTIVE,
        email_verified=True,
    )

    with pytest.raises(AppException) as error:
        await AuthService.validate_user_access(user)

    assert error.value.status_code == 403
    assert error.value.code == ErrorCode.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_validate_user_access_allows_platform_role():
    user = SimpleNamespace(
        is_deleted=False,
        status=UserStatus.ACTIVE,
        email_verified=True,
        role=Role.ADMIN,
        business_id=None,
    )

    await AuthService.validate_user_access(user)


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email():
    with patch("app.domains.auth.services.User") as user_model:
        user_model.find_one = AsyncMock(return_value=object())

        with pytest.raises(AppException) as error:
            await AuthService.register_self(
                SimpleNamespace(email="exists@example.com"),
                SimpleNamespace(name="Business"),
                MagicMock(),
                MagicMock(),
            )

    assert error.value.status_code == 409
    assert error.value.code == ErrorCode.EMAIL_ALREADY_REGISTERED


@pytest.mark.asyncio
async def test_register_rejects_invalid_business_slug():
    with (
        patch("app.domains.auth.services.User") as user_model,
        patch("app.domains.auth.services.generate_slug", return_value=""),
    ):
        user_model.find_one = AsyncMock(return_value=None)

        with pytest.raises(AppException) as error:
            await AuthService.register_self(
                SimpleNamespace(email="new@example.com"),
                SimpleNamespace(name="Invalid"),
                MagicMock(),
                MagicMock(),
            )

    assert error.value.status_code == 400
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_login_returns_access_refresh_and_csrf_tokens(test_settings):
    user = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        email="user@example.com",
        password_hash="hashed-password",
        role=Role.ADMIN,
        business_id=None,
        is_deleted=False,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    session = MagicMock()
    session.insert = AsyncMock()

    with (
        patch("app.domains.auth.services.User") as user_model,
        patch("app.domains.auth.services.verify_password", return_value=True),
        patch("app.domains.auth.services.create_access_token", return_value="access"),
        patch("app.domains.auth.services.create_refresh_token", return_value="refresh"),
        patch("app.domains.auth.services.create_csrf_token", return_value="csrf"),
        patch("app.domains.auth.services.AuthSession", return_value=session),
    ):
        user_model.find_one = AsyncMock(return_value=user)
        result = await AuthService.login(
            UserLogin(email="user@example.com", password="Password123"),
            test_settings,
        )

    assert result.access_token == "access"
    assert result.refresh_token == "refresh"
    assert result.csrf_token == "csrf"
    session.insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_uses_same_public_error_for_unknown_user():
    with (
        patch("app.domains.auth.services.User") as user_model,
        patch("app.domains.auth.services.verify_password", return_value=False),
    ):
        user_model.find_one = AsyncMock(return_value=None)

        with pytest.raises(AppException) as error:
            await AuthService.login(
                UserLogin(email="unknown@example.com", password="wrong"),
                MagicMock(),
            )

    assert error.value.status_code == 401
    assert error.value.code == ErrorCode.AUTHENTICATION_FAILED


@pytest.mark.asyncio
async def test_refresh_requires_cookie():
    with pytest.raises(AppException) as error:
        await AuthService.refresh(None, None, MagicMock())

    assert error.value.status_code == 401
    assert error.value.code == ErrorCode.REFRESH_FAILED


@pytest.mark.asyncio
async def test_refresh_rejects_invalid_csrf(test_settings):
    with patch("app.domains.auth.services.verify_csrf_token", return_value=False):
        with pytest.raises(AppException) as error:
            await AuthService.refresh("refresh", "csrf", test_settings)

    assert error.value.status_code == 403
    assert error.value.code == ErrorCode.CSRF_INVALID


@pytest.mark.asyncio
async def test_refresh_rejects_expired_session(test_settings):
    session = SimpleNamespace(
        revoked_at=None,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    with (
        patch("app.domains.auth.services.verify_csrf_token", return_value=True),
        patch("app.domains.auth.services.AuthSession") as session_model,
    ):
        session_model.find_one = AsyncMock(return_value=session)

        with pytest.raises(AppException) as error:
            await AuthService.refresh("refresh", "csrf", test_settings)

    assert error.value.status_code == 401
    assert error.value.code == ErrorCode.REFRESH_FAILED


@pytest.mark.asyncio
async def test_logout_without_cookie_is_idempotent(test_settings):
    await AuthService.logout(None, None, test_settings)
