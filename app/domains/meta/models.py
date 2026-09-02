from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel

from app.core.base_model import BaseDocument
from app.shared.enums import FrontendType, TitlePosition

class ThemeColors(BaseModel):
    one: str = "#1C1917"
    one_d: str = "#0C0A09"
    two: str = "#57534E"
    two_d: str = "#44403C"
    three: str = "#8C6A43"
    three_d: str = "#6F5233"
    four: str = "#C7B9A5"
    four_d: str = "#A89273"
    five: str = "#EDE8E0"
    five_d: str = "#D8CFC2"
    background: str = "#FAF9F6"

class Meta(BaseDocument):
    business_id: Indexed(PydanticObjectId, unique=True)

    # Apariencia
    show_title: bool = True
    title_position: TitlePosition = TitlePosition.CENTER
    template: int=1
    colors: ThemeColors = Field(default_factory=ThemeColors)
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