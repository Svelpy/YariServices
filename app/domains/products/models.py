from pydantic import BaseModel, Field
from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING
from app.core.base_model import BaseDocument  

# --- ESQUEMA AUXILIAR PARA ATRIBUTOS DINÁMICOS ---
class ProductAttribute(BaseModel):
    key: str    # Identificador técnico
    value: str  # Valor real
    label: str  # Nombre visible en el frontend


# --- MODELO DE PRODUCTO (ETAPA 1) ---
class Product(BaseDocument):
    # --- Control de Empresa e Identificación ---
    business_id: PydanticObjectId   # El "Tenant" / Empresa dueña del producto
    barcode: str | None = None              
    sku: str | None = None                   
    slug: str                     
    
    # --- Datos Básicos ---
    name: str                               
    presentation: str | None = None         
    category_id: PydanticObjectId | None = None   #
    brand: str | None = None # en un futuro sera otra tabla                 
    description: str | None = None           
    # revisar todos los costos 
    # --- Financieros e Inventario Plano (Etapa 1) ---
    price: float = Field(default=0.0, ge=0)
    price_discount: float | None = None                

    stock: int = Field(default=0, ge=0)
    min_stock: int = Field(default=5, ge=0)
    #estudiar unidad de medida

    # --- Galería de Imágenes (Cloudinary) ---
    images: list[str] = Field(default_factory=list)
    
    display_order: int = Field(default=0)
    # --- Atributos Polimórficos Multi-Rubro ---
    attributes: list[ProductAttribute] = Field(default_factory=list)

    # --- Control ---
    is_active: bool = True

    class Settings:
        name = "products"
        indexes = [
            # Código de barras único por empresa (ignora nulos)
            IndexModel([("business_id", ASCENDING), ("barcode", ASCENDING)],unique=True,partialFilterExpression={"barcode": {"$type": "string"}}),
            # slug único por empresa
            IndexModel([("business_id", ASCENDING), ("slug", ASCENDING)], unique=True),
            # sku único por empresa, solo si existe
            IndexModel([("business_id", ASCENDING), ("sku", ASCENDING)],unique=True,partialFilterExpression={"sku": {"$type": "string"}}),
            # Búsqueda rápida por Empresa y Categoría
            IndexModel([("business_id", ASCENDING), ("category_id", ASCENDING)]),
            # Filtros rápidos de activos en el frontend
            IndexModel([("business_id", ASCENDING), ("is_active", ASCENDING)]),
            # Búsqueda por cualquier atributo dinámico (multi-rubro)
            IndexModel([("business_id", ASCENDING),("attributes.key", ASCENDING),("attributes.value", ASCENDING)])
        ]

    def __repr__(self):
        return f"<Product {self.name} ({self.business_id})>"

    def __str__(self):
        return self.name