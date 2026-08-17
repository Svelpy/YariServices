from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.shared.enums import AuthProvider, Role, UserStatus
from app.shared.services.validators import (
    validator_names,
    validator_password,
    validator_phone,
    validator_username,
)


# ---------------------------------------------------------------------------
# Schemas de escritura (entrada de datos)
# ---------------------------------------------------------------------------

class UserRegistrationData(BaseModel):
    """Schema para auto-registro público."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)



    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validator_password(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "usuario@adamgroup.com.bo",
                "password": "Passw0rd123",
            }
        }
    )


class UserCreate(UserRegistrationData):
    """Schema para crear un usuario desde el panel administrativo."""

    name: str | None = Field(None, min_length=2, max_length=50)
    lastname: str | None = Field(None, min_length=2, max_length=100)
    username: str | None = Field(None, min_length=4, max_length=20)
    phone_number: str | None = Field(None, min_length=6, max_length=16)
    birth_date: datetime | None = None

    role: Role = Role.USER
    
    @field_validator("name", "lastname")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return validator_names(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        return validator_username(value)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return validator_phone(value)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "admin.creado@adamgroup.com.bo",
                "password": "Passw0rd123",
                "role": "GERENTE",
            }
        }
    )


class UserSelfUpdate(BaseModel):
    """Schema para actualizar datos del propio usuario."""

    name: str | None = Field(None, min_length=2, max_length=50)
    lastname: str | None = Field(None, min_length=2, max_length=100)
    username: str | None = Field(None, min_length=4, max_length=20)
    phone_number: str | None = Field(None, min_length=5, max_length=15)
    birth_date: datetime | None = None

    @field_validator("name", "lastname")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return validator_names(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        return validator_username(value)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return validator_phone(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "María",
                "phone_number": "+59170099887",
            }
        }
    )
    

from typing import Literal
AdministrativeUserStatus = Literal[UserStatus.ACTIVE,UserStatus.INACTIVE,UserStatus.SUSPENDED,UserStatus.BANNED]
class UserUpdate(UserSelfUpdate):
    """Schema para actualizar un usuario desde una ruta administrativa."""
    
    role: Role | None = None
    status: AdministrativeUserStatus | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "María",
                "status": "ACTIVE",
                "role": "GERENTE",
            }
        }
    )



class AdminResetPassword(BaseModel):
    """Schema para restablecer contraseñas administrativamente."""

    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validator_password(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_password": "NuevaPass123",
            }
        }
    )


class PasswordSelfUpdate(AdminResetPassword):
    """Schema para cambiar la contraseña del usuario autenticado."""

    current_password: str = Field(..., min_length=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "PassActual123",
                "new_password": "NuevaPass123",
            }
        }
    )


# ---------------------------------------------------------------------------
# Schemas de lectura (salida de datos)
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """Respuesta de usuario sin contraseña ni datos sensibles."""

    id: PydanticObjectId
    business_id: PydanticObjectId | None = None
    email: EmailStr
    name: str | None = None
    lastname: str | None = None
    username: str | None = None
    phone_number: str | None = None
    birth_date: datetime | None = None
    avatar_url: str | None = None
    auth_provider: AuthProvider
    email_verified: bool
    role: Role
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "business_id": "507f1f77bcf86cd799439000",
                "email": "usuario@adamgroup.com.bo",
                "name": "María",
                "lastname": "García López",
                "username": "mariagarcia",
                "role": "USER",
                "status": "ACTIVE",
                "email_verified": True,
                "auth_provider": "LOCAL",
                "avatar_url": None,
                "phone_number": "+59170012345",
                "birth_date": "1990-01-01T00:00:00Z",
                "created_at": "2025-12-19T14:00:00Z",
                "updated_at": "2025-12-19T14:00:00Z",
            }
        },
    )


class UserResponseAudit(UserResponse):
    created_by: PydanticObjectId | None = None
    updated_by: PydanticObjectId | None = None
    is_deleted: bool
    deleted_at: datetime | None = None
    deleted_by: PydanticObjectId | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "business_id": "507f1f77bcf86cd799439000",
                "email": "usuario@adamgroup.com.bo",
                "name": "María",
                "lastname": "García López",
                "username": "mariagarcia",
                "role": "USER",
                "status": "ACTIVE",
                "email_verified": True,
                "auth_provider": "LOCAL",
                "avatar_url": None,
                "phone_number": "+59170012345",
                "birth_date": "1990-01-01T00:00:00Z",
                "created_at": "2025-12-19T14:00:00Z",
                "updated_at": "2025-12-19T14:00:00Z",
                "created_by": "507f1f77bcf86cd799439000",
                "updated_by": "507f1f77bcf86cd799439000",
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
            }
        },
    )
