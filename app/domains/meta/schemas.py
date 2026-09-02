from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.enums import FrontendType, TitlePosition
from app.shared.services.validators import validator_custom_domain, validator_required_field


class ThemeColorsSchema(BaseModel):
    """Paleta de colores utilizada por el storefront."""

    one: str
    two: str
    three: str
    four: str
    five: str
    one_d: str
    two_d: str
    three_d: str
    four_d: str
    five_d: str
    background: str

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        json_schema_extra={
            "example": {
                "one": "#2563EB",
                "two": "#7C3AED",
                "three": "#DB2777",
                "four": "#EA580C",
                "five": "#16A34A",
                "one_d": "#1E3A8A",
                "two_d": "#4C1D95",
                "three_d": "#831843",
                "four_d": "#7C2D12",
                "five_d": "#14532D",
                "background": "#FFFFFF",
            }
        },
    )


class MetaMeUpdate(BaseModel):
    """Actualización parcial del storefront del negocio autenticado."""

    show_title: bool | None = None
    title_position: TitlePosition | None = None
    template: int | None = Field(default=None, ge=1)
    colors: ThemeColorsSchema | None = None
    design_type_card: int | None = Field(default=None, ge=1)

    seo_title: str | None = None
    seo_description: str | None = None

    maintenance_mode: bool | None = None

    social_links: dict[str, str] | None = None

    @field_validator(
        "show_title",
        "title_position",
        "template",
        "colors",
        "design_type_card",
        "maintenance_mode",
        "social_links",
    )
    @classmethod
    def validate_required_field(cls, value: object) -> object:
        return validator_required_field(value)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "show_title": False,
                "title_position": "left",
                "seo_title": "Nuevo título de Adam Group",
                "maintenance_mode": True,
            }
        },
    )


class MetaUpdate(MetaMeUpdate):
    """Actualización administrativa de la configuración del storefront."""

    custom_domain: str | None = Field(default=None, max_length=253)
    frontend_type: FrontendType | None = None

    @field_validator("custom_domain", mode="before")
    @classmethod
    def validate_custom_domain(cls, value: object) -> str | None:
        return validator_custom_domain(value)

    @field_validator("frontend_type")
    @classmethod
    def validate_frontend_type(cls, value: FrontendType | None) -> FrontendType:
        return validator_required_field(value)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "show_title": False,
                "custom_domain": "store.adamgroup.com",
                "frontend_type": "custom",
            }
        },
    )


class MetaResponse(BaseModel):
    """Representación de la configuración del storefront."""

    id: PydanticObjectId
    business_id: PydanticObjectId

    show_title: bool
    title_position: TitlePosition
    template: int
    colors: ThemeColorsSchema
    design_type_card: int

    seo_title: str | None = None
    seo_description: str | None = None
    og_image_url: str | None = None
    favicon_url: str | None = None

    maintenance_mode: bool
    config_version: int

    custom_domain: str | None = None
    frontend_type: FrontendType

    carousel_urls: list[str] = Field(default_factory=list)
    social_links: dict[str, str] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439020",
                "business_id": "507f1f77bcf86cd799439000",
                "show_title": True,
                "title_position": "center",
                "template": 1,
                "colors": ThemeColorsSchema.model_config["json_schema_extra"]["example"],
                "design_type_card": 1,
                "seo_title": "Adam Group | Tienda online",
                "seo_description": "Compra productos de Adam Group en línea.",
                "og_image_url": "https://cdn.example.com/storefront/og-image.png",
                "favicon_url": "https://cdn.example.com/storefront/favicon.png",
                "maintenance_mode": False,
                "config_version": 1,
                "custom_domain": "tienda.adamgroup.com",
                "frontend_type": "template",
                "carousel_urls": [
                    "https://cdn.example.com/storefront/carousel-1.png"
                ],
                "social_links": {
                    "facebook": "https://facebook.com/adamgroup",
                    "instagram": "https://instagram.com/adamgroup",
                },
                "created_at": "2026-09-01T12:00:00Z",
                "updated_at": "2026-09-01T12:00:00Z",
            }
        },
    )


class MetaResponseAudit(MetaResponse):
    """Representación de Meta con datos de auditoría."""

    created_by: PydanticObjectId | None = None
    updated_by: PydanticObjectId | None = None
    is_deleted: bool
    deleted_at: datetime | None = None
    deleted_by: PydanticObjectId | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                **MetaResponse.model_config["json_schema_extra"]["example"],
                "created_by": "507f1f77bcf86cd799439011",
                "updated_by": "507f1f77bcf86cd799439011",
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
            }
        },
    )
