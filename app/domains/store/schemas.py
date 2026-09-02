from pydantic import BaseModel, ConfigDict

from app.domains.bussines import BusinessResponse, BusinessResponseAudit
from app.domains.meta import MetaResponse, MetaResponseAudit


class StoreResponse(BaseModel):
    """Vista unificada del negocio y la configuración de su storefront."""

    business: BusinessResponse
    meta: MetaResponse

    model_config = ConfigDict(from_attributes=True)


class StoreResponseAudit(BaseModel):
    """Vista unificada de Store con datos de auditoría de plataforma."""

    business: BusinessResponseAudit
    meta: MetaResponseAudit

    model_config = ConfigDict(from_attributes=True)
