from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING
from datetime import datetime
from pydantic import EmailStr, Field
from app.shared.enums import BusinessPlan, FrontendType, BillingStatus
from app.core.base_model import BaseDocument


class Business(BaseDocument):
    # Identidad
    owner_id: Indexed(PydanticObjectId, unique=True)
    name: str  
    description: str | None = None
    logo_url: str | None = None
    carousel_url: list[str] = Field(default_factory=list)
    social_links: dict[str, str] = Field(default_factory=dict)
    # Contacto
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    address_google_maps_url: str | None = None
    # Identidad legal / fiscal
    legal_name: str | None = None
    tax_id: str | None = None
    country: str  = "BO"
    # Localización
    currency: str = "BOB" 
    # Routing
    frontend_type: FrontendType = FrontendType.TEMPLATE
    slug: Indexed(str, unique=True)
    custom_domain: str | None = None

    # Plan y facturación
    plan: BusinessPlan = BusinessPlan.BASICO
    plan_started_at: datetime
    plan_expires_at: datetime 
    billing_status: BillingStatus = BillingStatus.ACTIVE
    is_active: bool = True

    class Settings:
        name = "businesses"
        indexes = [
            "plan", 
            "billing_status",
            IndexModel([("custom_domain", ASCENDING)],unique=True,partialFilterExpression={"custom_domain": {"$type": "string"}}),
            IndexModel([("country", ASCENDING), ("tax_id", ASCENDING)],unique=True,partialFilterExpression={"tax_id": {"$type": "string"}})
            ]

    def __repr__(self):
        return f"<Business {self.name} ({self.slug})>"

    def __str__(self):
        return self.name