from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.shared.services.validators import validator_business_name, validator_currency


class BusinessRegistrationData(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def validate_business_name(cls, value: str) -> str:
        return validator_business_name(value)





class BusinessMeUpdate(BaseModel):
    """Campos que el propietario puede actualizar de su negocio."""
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    address_google_maps_url: str | None = Field(default=None, max_length=2048)
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("name", mode="before")
    @classmethod
    def validate_business_names(cls, value: str | None) -> str | None:
        return validator_business_name(value)

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validator_currency(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Adam Group Internacional",
                "description": "Nueva descripción del negocio.",
                "email": "contacto@adamgroup.com",
                "phone": "+591 70000000",
                "address": "Av. Principal 123, Santa Cruz, Bolivia",
                "address_google_maps_url": "https://maps.google.com/?q=Adam+Group",
                "currency": "BOB",
            }
        }
    )

class BusinessUpdate(BusinessMeUpdate):
    """Campos editables del negocio para actualizaciones parciales (PATCH)."""
    is_active: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Adam Group Internacional",
                "description": "Nueva descripción del negocio.",
                "email": "contacto@adamgroup.com",
                "phone": "+591 70000000",
                "address": "Av. Principal 123, Santa Cruz, Bolivia",
                "address_google_maps_url": "https://maps.google.com/?q=Adam+Group",
                "currency": "BOB",
                "is_active": True,
            }
        }
    )

class BusinessResponse(BaseModel):
    """Representación pública de un negocio y su configuración de tenant."""

    id: PydanticObjectId

    name: str
    slug: str
    description: str | None = None
    logo_url: str | None = None

    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    address_google_maps_url: str | None = None

    currency: str

    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439000",
                "name": "Adam Group S.R.L.",
                "description": "Distribuidora de productos para el hogar.",
                "logo_url": "https://cdn.example.com/businesses/adam-group/logo.png",
                "email": "contacto@adamgroup.com",
                "phone": "+591 70000000",
                "address": "Av. Principal 123, Santa Cruz, Bolivia",
                "address_google_maps_url": "https://maps.google.com/?q=Adam+Group",
                "currency": "BOB",
                "slug": "adam-group-srl",
                "is_active": True,
                "created_at": "2026-07-12T19:00:00Z",
                "updated_at": "2026-07-12T19:00:00Z",
            }
        }
    )





class BusinessResponseAudit(BusinessResponse):
    """Representación de negocio con metadatos de auditoría."""

    created_by: PydanticObjectId | None = None
    updated_by: PydanticObjectId | None = None
    is_deleted: bool
    deleted_at: datetime | None = None
    deleted_by: PydanticObjectId | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439000",
                "name": "Adam Group S.R.L.",
                "slug": "adam-group-srl",
                "description": "Distribuidora de productos para el hogar.",
                "logo_url": "https://cdn.example.com/businesses/adam-group/logo.png",
                "email": "contacto@adamgroup.com",
                "phone": "+591 70000000",
                "address": "Av. Principal 123, Santa Cruz, Bolivia",
                "address_google_maps_url": "https://maps.google.com/?q=Adam+Group",
                "currency": "BOB",
                "is_active": True,
                "created_at": "2026-07-12T19:00:00Z",
                "updated_at": "2026-07-12T19:00:00Z",
                "created_by": "507f1f77bcf86cd799439011",
                "updated_by": "507f1f77bcf86cd799439011",
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
            }
        }
    )
