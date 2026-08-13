from app.core.config import Settings, get_settings
from fastapi import APIRouter, Depends, Request, Response, status, Query
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from app.middlewares.limiter import limiter
from app.domains.auth.schemas import (
    EmailVerificationResponse,
    TokenResponse,
    UserLogin,
    CurrentUser,
)
from app.domains.auth.dependencies import require_roles
from app.domains.auth.services import AuthService
from app.domains.bussines import BusinessRegistrationData
from app.domains.users import UserRegistrationData, UserResponse
from pymongo import AsyncMongoClient
from app.core.database import get_mongodb_client
from app.shared.enums import Role

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register",status_code=status.HTTP_201_CREATED,response_model=UserResponse)
@limiter.limit("5/hour")
async def register(
    request: Request,
    user: UserRegistrationData,
    business: BusinessRegistrationData,
    _: Annotated[CurrentUser,Depends(require_roles(Role.SUPERADMIN, Role.ADMIN))],
    mongodb_client: Annotated[AsyncMongoClient,Depends(get_mongodb_client)],
    settings: Annotated[Settings,Depends(get_settings)],
):
    """Registra un propietario y crea su negocio."""

    return await AuthService.register_self(user,business,mongodb_client,settings)

@router.get("/verify-email", response_model=EmailVerificationResponse)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    token: Annotated[str, Query(min_length=20)],
    mongodb_client: Annotated[AsyncMongoClient,Depends(get_mongodb_client)],
) -> EmailVerificationResponse:
    """Verifica usuario y negocio usando email"""

    return await AuthService.verify_email(token,mongodb_client)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """
    Iniciar sesión con correo y contraseña.
    
    Emite un token JWT de acceso válido.
    """
    credentials = UserLogin(email=form_data.username,password=form_data.password)
    tokens = await AuthService.login(credentials, settings)
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )
    return TokenResponse(
        access_token=tokens.access_token,
        token_type="bearer",
    )

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    refresh_token = request.cookies.get(
        settings.REFRESH_TOKEN_COOKIE_NAME
    )

    tokens = await AuthService.refresh(
        refresh_token,
        settings,
    )

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=tokens.access_token,
        token_type="bearer",
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    refresh_token = request.cookies.get(
        settings.REFRESH_TOKEN_COOKIE_NAME
    )

    await AuthService.logout(refresh_token)

    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path="/api/v1/auth",
    )



