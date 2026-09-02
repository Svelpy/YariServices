from app.shared.services.permissions import PLATFORM_ROLES
from datetime import datetime, timedelta, timezone
from app.shared.errors.codes import ErrorCode
from app.shared.errors.exceptions import AppException
from uuid import UUID
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.asynchronous.client_session import AsyncClientSession
from app.domains.auth.models import AuthSession, EmailVerificationToken
from app.domains.auth.schemas import AuthTokens, UserLogin, RegistrationResponse, CurrentUser
from app.domains.users import User, UserRegistrationData
from app.domains.bussines import Business, BusinessRegistrationData
from app.domains.meta import Meta
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_csrf_token,
    create_one_time_token,
    hash_one_time_token,
)
from urllib.parse import urlencode
from app.integrations.resend import ResendService
from app.core.config import Settings
from app.shared.enums import AuthProvider, Role, UserStatus
from app.shared.services.slug import generate_slug

class AuthService:
    VERIFICATION_TOKEN_EXPIRE_HOURS = 24

    @staticmethod
    async def validate_user_access(user: User) -> None:
        """Valida el estado de la cuenta y del negocio asociado."""
        if user.is_deleted:
            raise AppException("Usuario no disponible.", 401, ErrorCode.AUTHENTICATION_FAILED)

        if user.status != UserStatus.ACTIVE or not user.email_verified:
            raise AppException("Usuario inactivo o correo no verificado.", 403, ErrorCode.PERMISSION_DENIED)

        if user.role in PLATFORM_ROLES:
            return

        if user.business_id is None:
            raise AppException("El usuario no tiene un negocio asignado.", 403, ErrorCode.PERMISSION_DENIED)

        business = await Business.get(user.business_id)

        if business is None or business.is_deleted:
            raise AppException("El negocio no esta disponible.", 403, ErrorCode.PERMISSION_DENIED)

        if not business.is_active:
            raise AppException("El negocio esta inactivo.", 403, ErrorCode.PERMISSION_DENIED)




    @staticmethod
    async def deliver_verification_email(
        email: str,
        token_value: str,
        settings: Settings,
        *,
        is_resend: bool = False,
    ) -> None:
        verification_url = (
            f"{settings.AUTH_FRONTEND_URL.rstrip('/')}/verify-email?"
            f"{urlencode({'token': token_value})}"
        )
        if is_resend:
            message = "Generamos un nuevo enlace para activar tu cuenta."
        else:
            message = "Confirma tu correo electrónico para activar tu cuenta."

        await ResendService.send_email(
            settings,
            to=email,
            subject="Verifica tu correo electronico",
            html=f"""
                <h1>Verifica tu correo</h1>
                <p>{message}</p>
                <p>
                    <a href="{verification_url}">
                        Verificar correo electronico
                    </a>
                </p>
                <p>Este enlace expira en 24 horas.</p>
            """,
            text=f"{message} Usa este enlace: {verification_url}",
        )


    @staticmethod
    async def register_self(
        user_data: UserRegistrationData,
        business_data: BusinessRegistrationData,
        actor: CurrentUser,
        mongodb_client: AsyncMongoClient,
        settings: Settings,
    ) -> RegistrationResponse:
        """Registra un propietario y crea su negocio."""
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise AppException("El email ya está registrado.", 409, ErrorCode.EMAIL_ALREADY_REGISTERED)

        business_slug = generate_slug(business_data.name)
        if not business_slug:
            raise AppException("El nombre del negocio no genera un slug válido.", 400, ErrorCode.VALIDATION_ERROR)

        existing_business = await Business.find_one(Business.slug == business_slug)
        if existing_business:
            raise AppException("El nombre del negocio ya está registrado.", 409, ErrorCode.BUSINESS_ALREADY_REGISTERED)


        now = datetime.now(timezone.utc)
        password_hash = hash_password(user_data.password)

        async def create_registration(session: AsyncClientSession) -> tuple[Business, User, str]:

            new_business = Business(
                name=business_data.name,
                slug=business_slug,
                created_by=actor.id
            )
            await new_business.insert(session=session)

            new_meta = Meta(
                business_id=new_business.id,
                created_by=actor.id,
            )
            await new_meta.insert(session=session)

            created_user = User(
                email=user_data.email,
                password_hash=password_hash,
                business_id=new_business.id,
                role=Role.PROPIETARIO,
                status=UserStatus.PENDING_VERIFICATION,
                email_verified=False,
                auth_provider=AuthProvider.LOCAL,
                created_by=actor.id,
            )
            await created_user.insert(session=session)

            verification_token_value = create_one_time_token()
            verification_token = EmailVerificationToken(
                user_id=created_user.id,
                token_hash=hash_one_time_token(verification_token_value),
                expires_at=now + timedelta(hours=AuthService.VERIFICATION_TOKEN_EXPIRE_HOURS),
            )
            await verification_token.insert(session=session)
            return new_business, created_user, verification_token_value

        try:
            async with mongodb_client.start_session() as session:
                new_business, created_user, verification_token_value=await session.with_transaction(create_registration)
        except DuplicateKeyError as error:
            raise AppException("El email, username o negocio ya está registrado.", 409, ErrorCode.CONFLICT) from error

        verification_email_sent = True
        try:
            await AuthService.deliver_verification_email(
                email=str(created_user.email),
                token_value=verification_token_value,
                settings=settings,
            )
        except Exception:
            verification_email_sent = False
        return RegistrationResponse(
            user_id=created_user.id,
            business_id=created_user.business_id,
            email=created_user.email,
            verification_email_sent=verification_email_sent,
            message=(
                "Registro creado y correo de verificación enviado."
                if verification_email_sent
                else "Registro creado, pero no se pudo enviar el correo."
            ),
        )
    


    @staticmethod
    async def verify_email(token: str,mongodb_client: AsyncMongoClient) -> dict[str, str]:
        token_hash = hash_one_time_token(token)
        now = datetime.now(timezone.utc)

        async def verify_registration(session: AsyncClientSession) -> dict[str, str]:
            verification_token = await EmailVerificationToken.find_one(
                {
                    "token_hash": token_hash,
                    "used_at": None,
                    "revoked_at": None,
                    "expires_at": {"$gt": now},
                },
                session=session,
            )

            if verification_token is None:
                raise AppException("El token es inválido, usado, revocado o expiró.", 400, ErrorCode.VERIFICATION_TOKEN_INVALID)

            user = await User.get(verification_token.user_id,session=session)
            if (user is None or user.is_deleted or user.email_verified or user.status != UserStatus.PENDING_VERIFICATION):
                raise AppException("El token es inválido, usado o expiró.", 400, ErrorCode.VERIFICATION_TOKEN_INVALID)

            business = None
            if user.role in PLATFORM_ROLES:
                pass
            else:
                if user.business_id is None:
                    raise AppException("El token es inválido, usado o expiró.", 400, ErrorCode.VERIFICATION_TOKEN_INVALID)

                business = await Business.get(user.business_id,session=session)
                if business is None or business.is_deleted:
                    raise AppException("El token es inválido, usado o expiró.", 400, ErrorCode.VERIFICATION_TOKEN_INVALID)

            verification_token.used_at = now
            await verification_token.save(session=session)

            user.email_verified = True
            user.status = UserStatus.ACTIVE
            await user.save(session=session)

            if (business is not None and user.role == Role.PROPIETARIO and not business.is_active):
                business.is_active = True
                await business.save(session=session)
            return {"message": "Correo verificado correctamente."}

        async with mongodb_client.start_session() as session:
            return await session.with_transaction(verify_registration)


    @staticmethod
    async def resend_verification(email: str,mongodb_client: AsyncMongoClient,settings: Settings) -> dict[str, str]:
        """Emite un nuevo enlace de verificacion sin revelar si existe la cuenta."""

        generic_response = {"message": "Si el correo corresponde a una cuenta pendiente de verificación, recibirá un nuevo enlace."}

        user = await User.find_one(User.email == email,User.is_deleted == False)
        if (user is None or user.email_verified or user.status != UserStatus.PENDING_VERIFICATION):
            return generic_response

        now = datetime.now(timezone.utc)

        async def replace_verification_token(session: AsyncClientSession) -> tuple[str, str] | None:

            current_user = await User.get(user.id, session=session)
            if (current_user is None or current_user.is_deleted or current_user.email_verified or current_user.status != UserStatus.PENDING_VERIFICATION):
                return None

            if current_user.role not in PLATFORM_ROLES:
                if current_user.business_id is None:
                    return None
                business = await Business.get(current_user.business_id,session=session)
                if business is None or business.is_deleted:
                    return None

            await EmailVerificationToken.find(
                EmailVerificationToken.user_id == current_user.id,
                EmailVerificationToken.used_at == None,
                EmailVerificationToken.revoked_at == None,
            ).update({"$set": {"revoked_at": now}},session=session)

            verification_token_value = create_one_time_token()

            verification_token = EmailVerificationToken(
                user_id=current_user.id,
                token_hash=hash_one_time_token(verification_token_value),
                expires_at=now + timedelta(hours=AuthService.VERIFICATION_TOKEN_EXPIRE_HOURS),
            )

            await verification_token.insert(session=session)

            verification_email = str(current_user.email)
            return verification_token_value,verification_email

        async with mongodb_client.start_session() as session:
            result = await session.with_transaction(replace_verification_token)

        if result is None:
            return generic_response
        verification_token_value, verification_email = result


        await AuthService.deliver_verification_email(
            email=verification_email,
            token_value=verification_token_value,
            settings=settings,
            is_resend=True,
        )

        return generic_response



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
            raise AppException("Email o contraseña incorrectos.", 401, ErrorCode.AUTHENTICATION_FAILED)
       
        await AuthService.validate_user_access(user)

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
        csrf_token = create_csrf_token(refresh_token, settings)

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
            csrf_token=csrf_token,
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
    async def refresh(refresh_token: str | None,csrf_token: str | None,settings: Settings) -> AuthTokens:
        if not refresh_token:
            raise AppException("Refresh token requerido.", 401, ErrorCode.REFRESH_FAILED)
        if not csrf_token or not verify_csrf_token(refresh_token,csrf_token,settings):
            raise AppException("CSRF token inválido.", 403, ErrorCode.CSRF_INVALID)

        now = datetime.now(timezone.utc)

        session = await AuthSession.find_one(AuthSession.refresh_token_hash == hash_refresh_token(refresh_token))

        if session is None:
            raise AppException("Refresh token inválido.", 401, ErrorCode.REFRESH_FAILED)
        
        if session.revoked_at is not None:
            if (session.revocation_reason == "rotated"and session.replaced_by is not None):
                await AuthService.revoke_session_family(session.family_id,"reuse_detected")
            raise AppException("Refresh token ya utilizado.", 401, ErrorCode.REFRESH_FAILED)

        if session.expires_at <= now:
            raise AppException("Refresh token expirado.", 401, ErrorCode.REFRESH_FAILED)

        user = await User.get(session.user_id)

        if user is None:
            raise AppException("Usuario no encontrado.", 401, ErrorCode.REFRESH_FAILED)

        await AuthService.validate_user_access(user)

        new_refresh_token = create_refresh_token()
        new_csrf_token = create_csrf_token(new_refresh_token,settings)
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
            raise AppException("Refresh token inválido o ya utilizado.",401,ErrorCode.REFRESH_FAILED)

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
            csrf_token=new_csrf_token,
        )
    
    @staticmethod
    async def logout(refresh_token: str | None,csrf_token: str | None,settings: Settings) -> None:
        if not refresh_token:
            return
        if not csrf_token or not verify_csrf_token(refresh_token,csrf_token,settings):
            raise AppException("CSRF token inválido.",403, ErrorCode.CSRF_INVALID)
        session = await AuthSession.find_one(AuthSession.refresh_token_hash == hash_refresh_token(refresh_token))

        if session is None or session.revoked_at is not None:
            return

        session.revoked_at = datetime.now(timezone.utc)
        session.last_used_at = session.revoked_at
        session.revocation_reason = "logout"

        await session.save()
