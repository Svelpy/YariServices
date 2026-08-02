import re
from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductAttributeSchema(BaseModel):
    """Schema para atributos dinámicos polimórficos multi-rubro"""

    key: str = Field(..., max_length=50, description="Identificador técnico (ej: color, talla, memoria)")
    value: str = Field(..., max_length=200, description="Valor real (ej: Rojo, XL, 128GB)")
    label: str = Field(..., max_length=50, description="Nombre visible en el frontend (ej: Color, Talla)")


class ProductCreate(BaseModel):
    """Schema para crear un nuevo producto"""

    name: str = Field(..., min_length=2, max_length=100)
    barcode: str | None = Field(default=None, max_length=50)
    sku: str | None = Field(default=None, max_length=50)
    presentation: str | None = Field(default=None, max_length=50)
    category_id: PydanticObjectId | None = None
    brand: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)

    cost: float = Field(default=0.0, ge=0)
    sale_price: float = Field(default=0.0, ge=0)
    wholesale_price: float | None = Field(default=None, ge=0)
    min_stock: int = Field(default=5, ge=0)

    attributes: list[ProductAttributeSchema] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list, description="Lista de URLs de imágenes almacenadas en Cloudinary")
    is_active: bool = True

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s&'./#_-]+$", v):
            raise ValueError('Nombre de producto contiene caracteres no válidos')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Laptop HP Pavilion 15",
                "barcode": "7791234567890",
                "sku": "HP-PAV-15-ROJO",
                "presentation": "Unidad",
                "brand": "HP",
                "description": "Portátil HP Pavilion 15 con procesador Intel i7 y 16GB RAM",
                "cost": 650.0,
                "sale_price": 850.0,
                "wholesale_price": 780.0,
                "min_stock": 3,
                "attributes": [
                    {"key": "color", "value": "Plata", "label": "Color"},
                    {"key": "ram", "value": "16GB", "label": "Memoria RAM"},
                ],
                "is_active": True,
            }
        }
    )


class ProductUpdate(BaseModel):
    """Schema para actualizar un producto (PATCH parcial). Todos los campos son opcionales."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    barcode: str | None = Field(default=None, max_length=50)
    sku: str | None = Field(default=None, max_length=50)
    presentation: str | None = Field(default=None, max_length=50)
    category_id: PydanticObjectId | None = None
    brand: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)

    cost: float | None = Field(default=None, ge=0)
    sale_price: float | None = Field(default=None, ge=0)
    wholesale_price: float | None = Field(default=None, ge=0)
    min_stock: int | None = Field(default=None, ge=0)

    attributes: list[ProductAttributeSchema] | None = None
    images: list[str] | None = Field(default=None, description="Lista de URLs de imágenes para reemplazar o actualizar")
    is_active: bool | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s&'./#_-]+$", v):
            raise ValueError('Nombre de producto contiene caracteres no válidos')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sale_price": 820.0,
                "min_stock": 5,
                "is_active": True,
            }
        }
    )


class ProductResponse(BaseModel):
    """Schema de respuesta estándar para un producto"""

    id: PydanticObjectId
    business_id: PydanticObjectId
    name: str
    slug: str
    barcode: str | None = None
    sku: str | None = None
    presentation: str | None = None
    category_id: PydanticObjectId | None = None
    brand: str | None = None
    description: str | None = None

    cost: float
    sale_price: float
    wholesale_price: float | None = None
    min_stock: int

    attributes: list[ProductAttributeSchema] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439099",
                "business_id": "507f1f77bcf86cd799439000",
                "name": "Laptop HP Pavilion 15",
                "slug": "laptop-hp-pavilion-15",
                "barcode": "7791234567890",
                "sku": "HP-PAV-15-ROJO",
                "presentation": "Unidad",
                "category_id": "507f1f77bcf86cd799439012",
                "brand": "HP",
                "description": "Portátil HP Pavilion 15 con procesador Intel i7 y 16GB RAM",
                "cost": 650.0,
                "sale_price": 850.0,
                "wholesale_price": 780.0,
                "min_stock": 3,
                "attributes": [
                    {"key": "color", "value": "Plata", "label": "Color"},
                    {"key": "ram", "value": "16GB", "label": "Memoria RAM"},
                ],
                "is_active": True,
                "created_at": "2026-07-12T19:00:00Z",
                "updated_at": "2026-07-12T19:00:00Z",
            }
        }
    )


class ProductResponseAudit(ProductResponse):
    """Schema de respuesta para producto con auditoría"""

    created_by: PydanticObjectId | None = None
    updated_by: PydanticObjectId | None = None
    is_deleted: bool
    deleted_at: datetime | None = None
    deleted_by: PydanticObjectId | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439099",
                "business_id": "507f1f77bcf86cd799439000",
                "name": "Laptop HP Pavilion 15",
                "slug": "laptop-hp-pavilion-15",
                "barcode": "7791234567890",
                "sku": "HP-PAV-15-ROJO",
                "presentation": "Unidad",
                "category_id": "507f1f77bcf86cd799439012",
                "brand": "HP",
                "description": "Portátil HP Pavilion 15 con procesador Intel i7 y 16GB RAM",
                "cost": 650.0,
                "sale_price": 850.0,
                "wholesale_price": 780.0,
                "min_stock": 3,
                "attributes": [
                    {"key": "color", "value": "Plata", "label": "Color"},
                ],
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
