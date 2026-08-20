from app.domains.auth.schemas import CurrentUser
from beanie import PydanticObjectId
from fastapi import Depends, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

from app.domains.auth.schemas import TokenClaims
from app.domains.auth.services import AuthService
from app.core.repositories import TenantRepository
from app.core.security import decode_access_token
from app.core.config import Settings, get_settings
from app.shared.errors.codes import ErrorCode
from app.shared.errors.exceptions import AppException
from app.shared.enums import Action, Module, Role
from app.shared.services.permissions import (
    BUSINESS_ROLES,
    PLATFORM_ROLES,
    has_permission,
)
from app.domains.users import User


# auto_error=False permite que el header sea opcional (para endpoints públicos)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login",auto_error=False)

def _get_token_claims(token: str | None,settings: Settings) -> TokenClaims:
    if token is None:
        raise AppException("Token de autenticación requerido", status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_REQUIRED)

    payload = decode_access_token(token, settings)
    if payload is None:
        raise AppException("Token inválido", status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_INVALID)

    try:
        return TokenClaims.model_validate(payload)
    except ValidationError:
        raise AppException("Token inválido", status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_INVALID)



async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings=Depends(get_settings)) -> User:

    claims = _get_token_claims(token, settings)

    user = await User.get(claims.sub)
    if user is None:
        raise AppException("Token invalido", status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_INVALID)

    await AuthService.validate_user_access(user)
    
    return user

async def get_current_principal( user: User = Depends(get_current_user)) -> CurrentUser:
    return CurrentUser(id=user.id,role=user.role,business_id=user.business_id)

async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    settings: Settings=Depends(get_settings)) -> User | None:
    if token is None:
        return None
    return await get_current_user(token, settings)

async def get_current_principal_optional(user: User | None = Depends(get_current_user_optional)) -> CurrentUser | None:
    if user is None:
        return None
    return CurrentUser(id=user.id,role=user.role,business_id=user.business_id)




def require_roles(*allowed_roles: Role):
    async def dependency(current_user: CurrentUser = Depends(get_current_principal)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise AppException("No tenés permisos para realizar esta acción", status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED)
        return current_user
    return dependency


def require_permission(module: Module, action: Action):
    async def dependency(current_user: CurrentUser = Depends(get_current_principal)) -> CurrentUser:
        if not has_permission(current_user.role, module, action):#estudia has_perssion
            raise AppException("No tenés permisos para realizar esta acción", status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED)
        return current_user
    return dependency


def require_tenant_permission(module: Module, action: Action):
    async def dependency(
        current_user: CurrentUser = Depends(get_current_principal),
    ) -> CurrentUser:
        if current_user.role not in BUSINESS_ROLES or current_user.business_id is None:
            raise AppException(
                "El usuario no tiene permisos dentro de un tenant.",
                status.HTTP_403_FORBIDDEN,
                ErrorCode.PERMISSION_DENIED,
            )

        if not has_permission(current_user.role, module, action):
            raise AppException(
                "No tenÃ©s permisos para realizar esta acciÃ³n",
                status.HTTP_403_FORBIDDEN,
                ErrorCode.PERMISSION_DENIED,
            )

        return current_user

    return dependency


def require_platform_permission(module: Module, action: Action):
    async def dependency(
        current_user: CurrentUser = Depends(get_current_principal),
    ) -> CurrentUser:
        if current_user.role not in PLATFORM_ROLES:
            raise AppException(
                "Solo los usuarios de plataforma pueden realizar esta acciÃ³n.",
                status.HTTP_403_FORBIDDEN,
                ErrorCode.PERMISSION_DENIED,
            )

        if not has_permission(current_user.role, module, action):
            raise AppException(
                "No tenÃ©s permisos para realizar esta acciÃ³n",
                status.HTTP_403_FORBIDDEN,
                ErrorCode.PERMISSION_DENIED,
            )

        return current_user

    return dependency


async def resolve_authorized_business_id(
    business_id: PydanticObjectId | None = Query(None,description="ID de la empresa (requerido para roles de plataforma)"),
    current_user: CurrentUser = Depends(get_current_principal),
) -> PydanticObjectId:
    """
    Resuelve el tenant autorizado para la solicitud actual.

    - Roles de plataforma (SUPERADMIN y ADMIN): deben indicar el
      `business_id` objetivo en la petición.
    - Roles de negocio: nunca pueden indicar `business_id`; se utiliza el
      tenant asociado al usuario autenticado.

    El `business_id` enviado por un usuario de negocio se rechaza incluso
    cuando coincide con el tenant de su cuenta, para mantener una única
    fuente de contexto y evitar suplantaciones mediante parámetros.
    """
    if current_user.role in PLATFORM_ROLES:
        if business_id is None:
            raise AppException("El business_id es obligatorio para usuarios de plataforma.", status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR)
        return business_id

    if business_id is not None:
        raise AppException("Los usuarios de negocio no pueden especificar business_id.", status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED)

    if current_user.business_id is None:
        raise AppException("El usuario no tiene un negocio asignado.", status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED)

    return current_user.business_id


def create_repo(model):
    async def dependency(business_id: PydanticObjectId = Depends(resolve_authorized_business_id)):
        return TenantRepository(model, business_id)
    return dependency
