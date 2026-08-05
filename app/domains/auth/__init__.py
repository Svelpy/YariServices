from app.domains.auth.schemas import UserSelfRegister, UserLogin, TokenResponse
from app.domains.auth.services import AuthService
from app.domains.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_roles,
    require_permission,
    resolve_authorized_business_id,
)

__all__ = [
    # Schemas
    "UserSelfRegister",
    "UserLogin",
    "TokenResponse",
    # Servicio de dominio
    "AuthService",
    # FastAPI Dependencies (guards de autenticación y autorización)
    "get_current_user",
    "get_current_user_optional",
    "require_roles",
    "require_permission",
    "resolve_authorized_business_id",
]

