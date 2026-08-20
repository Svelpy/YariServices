from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_mongodb_client
from app.domains.auth.dependencies import get_current_principal
from app.domains.auth.routes import router
from app.domains.auth.schemas import AuthTokens, CurrentUser
from app.middlewares.exception_handlers import register_exception_handlers
from app.middlewares.limiter import get_rate_limit_service
from app.shared.enums import AuthProvider, Role, UserStatus


def create_route_test_client() -> TestClient:
    application = FastAPI()
    settings = Settings(
        ENVIRONMENT="test",
        SECRET_KEY="test-secret-key",
        MONGODB_URL="mongodb://localhost:27017",
        MONGODB_DB_NAME="yari_test",
        TEST_MONGODB_DB_NAME="yari_test",
        REDIS_URL="redis://localhost:6379/15",
        DEV_ORIGINS="http://localhost:5173",
    )
    rate_limit_service = SimpleNamespace(check=AsyncMock())

    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_mongodb_client] = lambda: object()
    application.dependency_overrides[get_rate_limit_service] = lambda: rate_limit_service
    application.dependency_overrides[get_current_principal] = lambda: CurrentUser(
        id="507f1f77bcf86cd799439011",
        role=Role.ADMIN,
    )
    application.include_router(router)
    register_exception_handlers(application, settings)
    return TestClient(application)


def token_result() -> AuthTokens:
    return AuthTokens(
        access_token="access-token",
        refresh_token="refresh-token",
        csrf_token="csrf-token",
    )


def test_login_uses_oauth_form_and_sets_refresh_cookie():
    client = create_route_test_client()

    with patch(
        "app.domains.auth.routes.AuthService.login",
        new=AsyncMock(return_value=token_result()),
    ) as login:
        response = client.post(
            "/auth/login",
            data={"username": "user@example.com", "password": "Password123"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-token",
        "csrf_token": "csrf-token",
        "token_type": "bearer",
    }
    assert "refresh_token=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Path=/api/v1/auth" in response.headers["set-cookie"]
    assert "Cache-Control" in response.headers
    login.assert_awaited_once()


def test_login_rejects_json_instead_of_oauth_form():
    client = create_route_test_client()

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Password123"},
    )

    assert response.status_code == 422


def test_refresh_rotates_cookie_and_returns_new_csrf_token():
    client = create_route_test_client()
    client.cookies.set("refresh_token", "old-refresh-token")

    with patch(
        "app.domains.auth.routes.AuthService.refresh",
        new=AsyncMock(return_value=token_result()),
    ) as refresh:
        response = client.post(
            "/auth/refresh",
            headers={"X-CSRF-Token": "old-csrf-token"},
        )

    assert response.status_code == 200
    assert response.json()["csrf_token"] == "csrf-token"
    assert "refresh_token=" in response.headers["set-cookie"]
    refresh.assert_awaited_once_with(
        refresh_token="old-refresh-token",
        csrf_token="old-csrf-token",
        settings=refresh.call_args.kwargs["settings"],
    )


def test_logout_returns_204_and_deletes_cookie():
    client = create_route_test_client()
    client.cookies.set("refresh_token", "refresh-token")

    with patch(
        "app.domains.auth.routes.AuthService.logout",
        new=AsyncMock(),
    ) as logout:
        response = client.post(
            "/auth/logout",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert response.status_code == 204
    assert "refresh_token=" in response.headers["set-cookie"]
    logout.assert_awaited_once()


def test_register_requires_nested_user_and_business_body():
    client = create_route_test_client()
    user = {
        "id": "507f1f77bcf86cd799439011",
        "email": "owner@example.com",
        "auth_provider": AuthProvider.LOCAL.value,
        "email_verified": False,
        "role": Role.PROPIETARIO.value,
        "status": UserStatus.PENDING_VERIFICATION.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch(
        "app.domains.auth.routes.AuthService.register_self",
        new=AsyncMock(return_value=user),
    ) as register:
        response = client.post(
            "/auth/register",
            json={
                "user": {
                    "email": "owner@example.com",
                    "password": "Passw0rd123",
                },
                "business": {"name": "Business One"},
            },
        )

    assert response.status_code == 201
    assert response.json()["email"] == "owner@example.com"
    register.assert_awaited_once()
