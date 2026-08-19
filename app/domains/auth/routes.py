from typing import Annotated

from fastapi import APIRouter, Depends,Header, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from pymongo import AsyncMongoClient

from app.core.config import Settings, get_settings
from app.core.database import get_mongodb_client
from app.domains.auth.schemas import (
    CurrentUser,
    EmailVerificationRequest,
    EmailVerificationResponse,
    UserLogin,
    TokenResponse,
)
from app.domains.auth.dependencies import require_roles
from app.domains.auth.services import AuthService
from app.domains.bussines import BusinessRegistrationData
from app.domains.users import UserRegistrationData, UserResponse
from app.shared.enums import Role
from app.middlewares.limiter import (
    RateLimitService,
    get_rate_limit_service,
    rate_limit_ip_endpoint,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    dependencies=[Depends(rate_limit_ip_endpoint(
        "auth:register", "RATE_LIMIT_REGISTER_PER_HOUR", 3600
    ))],
)
async def register(
    user: UserRegistrationData,
    business: BusinessRegistrationData,
    _: Annotated[CurrentUser,Depends(require_roles(Role.SUPERADMIN, Role.ADMIN))],
    mongodb_client: Annotated[AsyncMongoClient,Depends(get_mongodb_client)],
    settings: Annotated[Settings,Depends(get_settings)],
):
    """Registra un propietario y crea su negocio."""

    return await AuthService.register_self(user,business,mongodb_client,settings)

@router.get(
    "/verify-email",
    response_model=EmailVerificationResponse,
    dependencies=[Depends(rate_limit_ip_endpoint(
        "auth:verify", "RATE_LIMIT_VERIFY_PER_MINUTE", 60
    ))],
)
async def verify_email(
    token: Annotated[str, Query(min_length=20)],
    mongodb_client: Annotated[AsyncMongoClient,Depends(get_mongodb_client)],
) -> EmailVerificationResponse:
    """Verifica usuario y negocio usando email"""

    return await AuthService.verify_email(token,mongodb_client)


@router.post(
    "/resend-verification",
    response_model=EmailVerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_ip_endpoint(
        "auth:resend", "RATE_LIMIT_RESEND_PER_HOUR", 3600
    ))],
)
async def resend_verification(
    verification_request: EmailVerificationRequest,
    mongodb_client: Annotated[AsyncMongoClient, Depends(get_mongodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    rate_limit_service: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> EmailVerificationResponse:
    """Solicita un nuevo enlace de verificacion por correo."""

    email = str(verification_request.email).strip().lower()
    await rate_limit_service.check(
        scope="email:resend",
        identity=email,
        limit=settings.RATE_LIMIT_RESEND_PER_HOUR,
        window_seconds=3600,
    )
    return await AuthService.resend_verification(
        email,
        mongodb_client,
        settings,
    )

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_ip_endpoint(
        "auth:login", "RATE_LIMIT_LOGIN_PER_MINUTE", 60
    ))],
)
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
    rate_limit_service: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> TokenResponse:
    """
    Iniciar sesión con correo y contraseña.
    
    Emite un token JWT de acceso válido.
    """
    email = form_data.username.strip().lower()
    await rate_limit_service.check(
        scope="email:login",
        identity=email,
        limit=settings.RATE_LIMIT_LOGIN_PER_MINUTE,
        window_seconds=60,
    )
    credentials = UserLogin(email=email,password=form_data.password)
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
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=tokens.access_token,
        csrf_token=tokens.csrf_token,
        token_type="bearer",
    )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_ip_endpoint(
        "auth:refresh", "RATE_LIMIT_REFRESH_PER_MINUTE", 60
    ))],
)
async def refresh(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    csrf_token: Annotated[str | None,Header(alias="X-CSRF-Token")] = None,
) -> TokenResponse:
    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    tokens = await AuthService.refresh(refresh_token=refresh_token,csrf_token=csrf_token,settings=settings)

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )

    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=tokens.access_token,
        csrf_token=tokens.csrf_token,
        token_type="bearer",
    )

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_ip_endpoint(
        "auth:logout", "RATE_LIMIT_LOGOUT_PER_MINUTE", 60
    ))],
)
async def logout(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    csrf_token: Annotated[str | None,Header(alias="X-CSRF-Token")] = None,
) -> None:
    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    await AuthService.logout(refresh_token=refresh_token,csrf_token=csrf_token,settings=settings)

    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path="/api/v1/auth",
    )



