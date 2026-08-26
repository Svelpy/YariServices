from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.shared.enums import Role
from app.shared.services.validators import validator_email 


class UserLogin(BaseModel):
    """Schema de entrada para login con email y contraseña"""
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validator_email(value)


class TokenResponse(BaseModel):
    """Schema de respuesta al autenticarse exitosamente"""
    access_token: str
    csrf_token: str
    token_type: str = "bearer"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "<jwt-access-token>",
                "csrf_token": "<csrf-token>",
                "token_type": "bearer",
            }
        }
    )
class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    csrf_token: str

class CurrentUser(BaseModel):
    id: PydanticObjectId
    role: Role
    business_id: PydanticObjectId | None = None

class TokenClaims(BaseModel):
    sub: PydanticObjectId
    role: Role
    business_id: PydanticObjectId | None = None
    iat: datetime
    exp: datetime
    jti: str

class EmailVerificationResponse(BaseModel):
    message: str

class RegistrationResponse(BaseModel):
    user_id: PydanticObjectId
    business_id: PydanticObjectId
    email: EmailStr
    verification_email_sent: bool
    message: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validator_email(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "usuario@ejemplo.com",
            }
        }
    )
