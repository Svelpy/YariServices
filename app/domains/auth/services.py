from datetime import datetime, timedelta, timezone
from app.shared.errors.exceptions import AppException
from uuid import UUID
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.asynchronous.client_session import AsyncClientSession
from app.domains.auth.models import AuthSession, EmailVerificationToken
from app.domains.auth.schemas import AuthTokens, UserLogin
from app.domains.users import User, UserRegistrationData
from app.domains.bussines import Business, BusinessRegistrationData
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    create_one_time_token,
    hash_one_time_token,
)
from urllib.parse import urlencode
from app.integrations.resend import ResendService
from app.core.config import Settings
from app.shared.enums import Role, UserStatus, AuthProvider
from app.shared.services.slug import generate_slug

class AuthService:
    @staticmethod
    async def register_self(
        user_data: UserRegistrationData,
        business_data: BusinessRegistrationData,
        mongodb_client: AsyncMongoClient,
        settings: Settings,
    ) -> User:
        """Registra un propietario y crea su negocio."""
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise AppException("El email ya está registrado.", 409)

        business_slug = generate_slug(business_data.name)
        if not business_slug:
            raise AppException("El nombre del negocio no genera un slug válido.",400)

        existing_business = await Business.find_one(Business.slug == business_slug)
        if existing_business:
            raise AppException("El nombre del negocio ya está registrado.", 409)


        now = datetime.now(timezone.utc)
        password_hash = hash_password(user_data.password)
        created_user: User | None = None
        verification_token_value: str | None = None

        async def create_registration(session) -> None:
            nonlocal created_user, verification_token_value

            new_business = Business(
                name=business_data.name,
                slug=business_slug,
                plan_started_at=now,
                plan_expires_at=now + timedelta(days=30),
            )

            await new_business.insert(session=session)

            created_user = User(
                email=user_data.email,
                password_hash=password_hash,
                business_id=new_business.id,
                role=Role.PROPIETARIO,
                status=UserStatus.PENDING_VERIFICATION,
                email_verified=False,
                auth_provider=AuthProvider.LOCAL,
            )

            await created_user.insert(session=session)

            verification_token_value = create_one_time_token()

            verification_token = EmailVerificationToken(
                user_id=created_user.id,
                token_hash=hash_one_time_token(verification_token_value),
                expires_at=now + timedelta(hours=24),
            )

            await verification_token.insert(session=session)

        try:
            async with mongodb_client.start_session() as session:
                await session.with_transaction(create_registration)
        except DuplicateKeyError as error:
            raise AppException("El email, username o negocio ya está registrado.",409) from error

        if created_user is None:
            raise AppException("No se pudo completar el registro.", 500)

        if verification_token_value is None:
            raise AppException("No se pudo crear el token de verificación.", 500)

        verification_url = (
            f"{settings.AUTH_FRONTEND_URL.rstrip('/')}/verify-email?"
            f"{urlencode({'token': verification_token_value})}"
        )

        await ResendService.send_email(
            settings,
            to=str(created_user.email),
            subject="Verifica tu correo electrónico",
            html=f"""
                <h1>Verifica tu correo</h1>
                <p>Confirma tu correo para activar tu cuenta.</p>
                <p>
                    <a href="{verification_url}">
                        Verificar correo electrónico
                    </a>
                </p>
                <p>Este enlace expira en 24 horas.</p>
            """,
            text=(f"Verifica tu correo electrónico usando este enlace: {verification_url}"),
        )
        return created_user
    


    @staticmethod
    async def verify_email(token: str,mongodb_client: AsyncMongoClient) -> dict[str, str]:
        token_hash = hash_one_time_token(token)
        now = datetime.now(timezone.utc)

        async def verify_registration(session: AsyncClientSession) -> dict[str, str]:
            verification_token = await EmailVerificationToken.find_one(
                {
                    "token_hash": token_hash,
                    "used_at": None,
                    "expires_at": {"$gt": now},
                },
                session=session,
            )

            if verification_token is None:
                raise AppException("El token es inválido, usado o expiró.",400)

            user = await User.get(verification_token.user_id,session=session)

            if user is None or user.business_id is None:
                raise AppException("Usuario no válido.", 400)

            business = await Business.get(user.business_id,session=session)

            if business is None:
                raise AppException("Negocio no válido.", 400)

            verification_token.used_at = now
            await verification_token.save(session=session)

            user.email_verified = True
            user.status = UserStatus.ACTIVE
            await user.save(session=session)

            business.is_active = True
            await business.save(session=session)

            return {"message": "Correo verificado correctamente."}

        async with mongodb_client.start_session() as session:
            return await session.with_transaction(verify_registration)




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
    