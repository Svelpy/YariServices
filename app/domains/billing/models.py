from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.base_model import BaseDocument
from app.shared.enums import BillingStatus


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PlanLimits(BaseModel):
    max_products: int | None = Field(default=None, ge=0)
    max_users: int | None = Field(default=None, ge=0)


class Plan(BaseDocument):
    code: str
    name: str
    description: str | None = None
    amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    limits: PlanLimits = Field(default_factory=PlanLimits)
    is_active: bool = True

    class Settings:
        name = "plans"
        indexes = [
            IndexModel([("code", ASCENDING)], unique=True),
        ]


class Subscription(BaseDocument):
    business_id: PydanticObjectId
    plan_id: PydanticObjectId
    status: BillingStatus = BillingStatus.ACTIVE

    # Importe y moneda congelados para esta suscripción.
    amount: Decimal = Field(ge=0)
    currency: str = "BOB"

    started_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    canceled_at: datetime | None = None

    class Settings:
        name = "subscriptions"
        indexes = [
            IndexModel(
                [("business_id", ASCENDING), ("status", ASCENDING)]
            ),
            IndexModel(
                [
                    ("business_id", ASCENDING),
                    ("current_period_end", DESCENDING),
                ]
            ),
        ]


class Invoice(BaseDocument):
    business_id: PydanticObjectId
    subscription_id: PydanticObjectId
    number: str

    amount: Decimal = Field(ge=0)
    currency: str = "BOB"
    status: InvoiceStatus = InvoiceStatus.DRAFT

    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    due_at: datetime
    paid_at: datetime | None = None

    class Settings:
        name = "invoices"
        indexes = [
            IndexModel(
                [("business_id", ASCENDING), ("number", ASCENDING)],
                unique=True,
            ),
            IndexModel(
                [
                    ("business_id", ASCENDING),
                    ("status", ASCENDING),
                    ("due_at", ASCENDING),
                ]
            ),
        ]


class Payment(BaseDocument):
    business_id: PydanticObjectId
    invoice_id: PydanticObjectId

    amount: Decimal = Field(ge=0)
    currency: str = "BOB"
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: str | None = None
    transaction_id: str | None = None
    paid_at: datetime | None = None

    class Settings:
        name = "payments"
        indexes = [
            IndexModel(
                [("business_id", ASCENDING), ("invoice_id", ASCENDING)]
            ),
            IndexModel(
                [("transaction_id", ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "transaction_id": {"$type": "string"}
                },
            ),
        ]
