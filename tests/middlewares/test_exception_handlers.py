from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.config import Settings
from app.middlewares.exception_handlers import register_exception_handlers
from app.shared.errors.codes import ErrorCode
from app.shared.errors.exceptions import AppException


def create_test_app() -> FastAPI:
    application = FastAPI()
    settings = Settings(ENVIRONMENT="test", SECRET_KEY="test-secret")
    register_exception_handlers(application, settings)

    @application.get("/app-error")
    async def app_error():
        raise AppException(
            "Token inválido",
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID,
        )

    @application.get("/http-error")
    async def http_error():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes",
            headers={"Retry-After": "30"},
        )

    class Input(BaseModel):
        password: str

    @application.post("/validation")
    async def validation(payload: Input):
        return payload

    return application


def test_app_exception_returns_stable_contract_and_bearer_header():
    client = TestClient(create_test_app())

    response = client.get("/app-error")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {
        "status": "fail",
        "code": "TOKEN_INVALID",
        "message": "Token inválido",
        "details": {},
    }


def test_http_exception_preserves_retry_after_header():
    client = TestClient(create_test_app())

    response = client.get("/http-error")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert response.json()["code"] == "HTTP_429"


def test_validation_error_uses_frontend_contract():
    client = TestClient(create_test_app())

    response = client.post("/validation", json={"password": 123})

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "fail"
    assert body["code"] == "VALIDATION_ERROR"
    assert "password" in body["details"]
