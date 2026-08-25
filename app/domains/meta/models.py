from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel

from app.core.base_model import BaseDocument
from app.shared.enums import FrontendType, TitlePosition

class ThemeColors(BaseModel):
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
    background:str
class Meta(BaseDocument):
    business_id: Indexed(PydanticObjectId, unique=True)

    # Apariencia
    show_title: bool = True
    title_position: TitlePosition = TitlePosition.CENTER
    template: int=1
    colors: ThemeColors
    design_type_card: int = 1

    # SEO / presencia social
    seo_title: str | None = None
    seo_description: str | None = None
    og_image_url: str | None = None
    favicon_url: str | None = None

    # Estado operativo
    maintenance_mode: bool = False

    # Forward-compatibility
    config_version: int = 1
    #Dominio y Frontend
    custom_domain: str | None = None
    frontend_type: FrontendType = FrontendType.TEMPLATE
    #Recursos Visuales
    carousel_urls: list[str] = Field(default_factory=list)
    social_links: dict[str, str] = Field(default_factory=dict)
    class Settings:
        name = "metas"
        indexes = [
                    IndexModel([("custom_domain", ASCENDING)],unique=True,partialFilterExpression={"custom_domain": {"$type": "string"}}),
                    ]