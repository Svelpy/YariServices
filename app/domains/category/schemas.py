import re
from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryCreate(BaseModel):
    """Schema para crear una nueva categoría"""

    name: str = Field(..., max_length=30)
    #slug: str = Field(..., max_length=30) debe hacerse en el servicio
    #path: str = Field(..., max_length=300) debe hacerse en el servicio
    description: str | None = Field(default=None, max_length=500)

    parent_id: PydanticObjectId | None = None
    #level: int = 0 debe hacerse en el servicio
    display_order: int = Field(default=0, ge=0)    #revisar

    banner_url: str | None = None
    is_active: bool = True

    meta_title: str | None = Field(default=None, max_length=50)
    meta_description: str | None = Field(default=None, max_length=200)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s'-]+$", v):
            raise ValueError('Solo se permiten letras, números, espacios, guiones y apóstrofes')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Laptops",
                "description": "Portátiles y notebooks",
                "parent_id": "507f1f77bcf86cd799439011",
                "display_order": 5,
                "banner_url": "https://res.cloudinary.com/.../laptops.jpg",
                "is_active": True,
                "meta_title": "Comprar Laptops y Portátiles",
                "meta_description": "Encuentra las mejores laptops de última generación al mejor precio.",
            }
        }
    )


class CategoryUpdate(BaseModel):
    """Schema para actualizar una categoría. Todos los campos son opcionales."""

    name: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=500)

    parent_id: PydanticObjectId | None = None
    display_order: int | None = Field(default=None, ge=0)

    banner_url: str | None = None
    is_active: bool | None = None

    meta_title: str | None = Field(default=None, max_length=50)
    meta_description: str | None = Field(default=None, max_length=200)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s'-]+$", v):
            raise ValueError('Solo se permiten letras, números, espacios, guiones y apóstrofes')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Laptops y Notebooks",
                "display_order": 3,
                "is_active": True,
            }
        }
    )


class CategoryResponse(BaseModel):
    """Schema de respuesta para categoría"""

    id: PydanticObjectId
    business_id: PydanticObjectId
    name: str
    slug: str
    path: str
    description: str | None = None
    parent_id: PydanticObjectId | None = None
    level: int
    display_order: int
    banner_url: str | None = None
    is_active: bool
    meta_title: str | None = None
    meta_description: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "business_id": "507f1f77bcf86cd799439000",
                "name": "Laptops",
                "slug": "laptops",
                "path": "electronics/laptops",
                "description": "Portátiles y notebooks",
                "parent_id": "507f1f77bcf86cd799439011",
                "level": 1,
                "display_order": 5,
                "banner_url": "https://res.cloudinary.com/.../laptops.jpg",
                "is_active": True,
                "meta_title": "Comprar Laptops y Portátiles",
                "meta_description": "Encuentra las mejores laptops de última generación al mejor precio.",
                "created_at": "2026-07-12T19:00:00Z",
                "updated_at": "2026-07-12T19:00:00Z",
            }
        }
    )


class CategoryResponseAudit(CategoryResponse):
    """Schema de respuesta para categoría con auditoría"""

    created_by: PydanticObjectId | None = None
    updated_by: PydanticObjectId | None = None
    is_deleted: bool
    deleted_at: datetime | None = None
    deleted_by: PydanticObjectId | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "business_id": "507f1f77bcf86cd799439000",
                "name": "Laptops",
                "slug": "laptops",
                "path": "electronics/laptops",
                "description": "Portátiles y notebooks",
                "parent_id": "507f1f77bcf86cd799439011",
                "level": 1,
                "display_order": 5,
                "banner_url": "https://res.cloudinary.com/.../laptops.jpg",
                "is_active": True,
                "meta_title": "Comprar Laptops y Portátiles",
                "meta_description": "Encuentra las mejores laptops de última generación al mejor precio.",
                "created_at": "2026-07-12T19:00:00Z",
                "updated_at": "2026-07-12T19:00:00Z",
                "created_by": "507f1f77bcf86cd799439000",
                "updated_by": "507f1f77bcf86cd799439000",
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
            }
        }
    )