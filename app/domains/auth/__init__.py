from app.domains.auth.models import AuthSession, EmailVerificationToken
from app.domains.auth.schemas import UserLogin, TokenResponse, CurrentUser, AuthTokens
from app.domains.auth.services import AuthService
from app.domains.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_roles,
    require_permission,
    require_tenant_permission,
    require_platform_permission,
    resolve_authorized_business_id,
)

__all__ = [
    #Models
    "AuthSession",
    "EmailVerificationToken",
    # Schemas
    "UserLogin",
    "TokenResponse",
    "CurrentUser",
    "AuthTokens",
    # Servicio de dominio
    "AuthService",
    # FastAPI Dependencies (guards de autenticación y autorización)
    "get_current_user",
    "get_current_user_optional",
    "require_roles",
    "require_permission",
    "require_tenant_permission",
    "require_platform_permission",
    "resolve_authorized_business_id",
]

