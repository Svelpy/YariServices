from datetime import datetime, timedelta, timezone
from app.shared.errors.exceptions import AppException
from uuid import UUID
from app.domains.users import User
from app.domains.auth.models import AuthSession
from app.domains.auth.schemas import AuthTokens, UserLogin, UserSelfRegister
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.config import Settings
from app.shared.enums import Role, UserStatus, AuthProvider

class AuthService:

    @staticmethod
    async def register_self(user_data: UserSelfRegister) -> User:
        """
        Autoregistro público de nuevos usuarios
        
        Args:
            user_data: Datos del usuario a registrar (role = USER por defecto)
            
        Returns:
            Usuario creado
        """
        username = None
        if user_data.username:
            cleaned_username = user_data.username.strip().lower()
            if cleaned_username != "":
                username = cleaned_username

        # Verificar si el email ya existe
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise AppException("El email ya está registrado.",409)
        
        # Verificar si el username ya existe
        if username!=None:
            existing_username = await User.find_one(User.username == username)
            if existing_username:
                raise AppException("El username ya está en uso.",409)
        
        # Crear nuevo usuario
        new_user = User(
            email=user_data.email,
            username=username,
            name=user_data.name,
            lastname=user_data.lastname,
            password_hash=hash_password(user_data.password),
            role=Role.USER,
            status=UserStatus.ACTIVE,
            email_verified=False,
            auth_provider=AuthProvider.LOCAL,
            avatar_url=None,
            phone_number=user_data.phone_number,
            birth_date=user_data.birth_date,
            created_by=None,
            updated_by=None
        )
        
        await new_user.save()
        return new_user

    @staticmethod
    async def login(credentials: UserLogin, settings: Settings) -> AuthTokens:
        """
        Autenticar usuario y generar token JWT
        
        Args:
            credentials: Email y contraseña
            
        Returns:
            Token de acceso y datos del usuario
        """
        # Buscar usuario por email
        user = await User.find_one(User.email == credentials.email, User.is_deleted == False)
        #se elije entre la contraseña hasheada o una contraseña hasheada pero falsa
        password_hash_to_verify = (
            user.password_hash 
            if user is not None and user.password_hash 
            else DUMMY_PASSWORD_HASH
        )
        #se verifica si la contraseña es valida
        password_is_valid = verify_password(credentials.password, password_hash_to_verify)
        if user is None or not password_is_valid:
            raise AppException("Email o contraseña incorrectos.",401)
        if user.status != UserStatus.ACTIVE:
            raise AppException("Usuario inactivo.",403)    
        # Crear token JWT
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "role": user.role.value,
                "business_id": (str(user.business_id) if (user.business_id is not None) else None),
            },
            settings=settings,
        )
        
        refresh_token = create_refresh_token()

        session = AuthSession(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        await session.insert()

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @staticmethod
    async def revoke_session_family(
        family_id: UUID,
        reason: str,
    ) -> None:
        await AuthSession.find(
            AuthSession.family_id == family_id,
            AuthSession.revoked_at == None,
        ).update(
            {
                "$set": {
                    "revoked_at": datetime.now(timezone.utc),
                    "revocation_reason": reason,
                }
            }
        )

    @staticmethod
    async def refresh(
        refresh_token: str | None,
        settings: Settings,
    ) -> AuthTokens:
        if not refresh_token:
            raise AppException("Refresh token requerido.", 401)

        now = datetime.now(timezone.utc)

        session = await AuthSession.find_one(
            AuthSession.refresh_token_hash == hash_refresh_token(refresh_token)
        )

        if session is None:
            raise AppException("Refresh token inválido.", 401)
        
        if session.revoked_at is not None:
            if (session.revocation_reason == "rotated"and session.replaced_by is not None):
                await AuthService.revoke_session_family(session.family_id,"reuse_detected")
            raise AppException("Refresh token ya utilizado.",401)

        if session.expires_at <= now:
            raise AppException("Refresh token expirado.", 401)

        user = await User.get(session.user_id)

        if user is None or user.is_deleted:
            raise AppException("Usuario no encontrado.", 401)

        if user.status != UserStatus.ACTIVE:
            raise AppException("Usuario inactivo.", 403)

        new_refresh_token = create_refresh_token()

        new_session = AuthSession(
            user_id=user.id,
            family_id=session.family_id,
            refresh_token_hash=hash_refresh_token(new_refresh_token),
            expires_at=now + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            ),
        )

        await new_session.insert()

        update_result = await AuthSession.find_one(
            AuthSession.id == session.id,
            AuthSession.revoked_at == None,
            AuthSession.expires_at > now,
        ).update(
            {
                "$set": {
                    "revoked_at": now,
                    "last_used_at": now,
                    "revocation_reason": "rotated",
                    "replaced_by": new_session.id,
                }
            }
        )

        if update_result.matched_count != 1:
            await new_session.delete()
            raise AppException(
                "Refresh token inválido o ya utilizado.",
                401,
            )

        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "role": user.role.value,
                "business_id": (
                    str(user.business_id)
                    if user.business_id is not None
                    else None
                ),
            },
            settings=settings,
        )

        return AuthTokens(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )
    
    @staticmethod
    async def logout(refresh_token: str | None) -> None:
        if not refresh_token:
            return

        session = await AuthSession.find_one(
            AuthSession.refresh_token_hash == hash_refresh_token(refresh_token)
        )

        if session is None or session.revoked_at is not None:
            return

        session.revoked_at = datetime.now(timezone.utc)
        session.last_used_at = session.revoked_at
        session.revocation_reason = "logout"

        await session.save()
