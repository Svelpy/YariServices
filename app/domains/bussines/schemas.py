import re
from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessCreate(BaseModel):
    """Schema para crear una nueva empresa/negocio"""

    name: str = Field(..., min_length=2, max_length=50)
    owner_id: PydanticObjectId  # Usuario asignado como Propietario

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s&'.-]+$", v):
            raise ValueError('Solo se permiten letras, números, espacios y caracteres comunes de empresas (&, -, .)')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Adam Group S.R.L.",
                "owner_id": "507f1f77bcf86cd799439011",
            }
        }
    )


class BusinessUpdate(BaseModel):
    """Schema para actualizar los datos de una empresa/negocio (PATCH parcial)"""

    name: str | None = Field(default=None, min_length=2, max_length=50)
    is_active: bool | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s&'.-]+$", v):
            raise ValueError('Solo se permiten letras, números, espacios y caracteres comunes de empresas (&, -, .)')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Adam Group Internacional",
                "is_active": True,
            }
        }
    )


class BusinessResponse(BaseModel):
    """Schema de respuesta pública/estándar de una empresa/negocio"""

    id: PydanticObjectId
    name: str
    slug: str
    owner_id: PydanticObjectId
    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439000",
                "name": "Adam Group S.R.L.",
                "slug": "adam-group-srl",
                "owner_id": "507f1f77bcf86cd799439011",
                "is_active": True,
                "created_at": "2026-07-12T19:00:00Z",
                "updated_at": "2026-07-12T19:00:00Z",
            }
        }
    )


class BusinessResponseAudit(BusinessResponse):
    """Schema de respuesta con datos de auditoría para administradores"""

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
                "owner_id": "507f1f77bcf86cd799439011",
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
