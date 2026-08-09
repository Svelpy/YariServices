# solo reexportamos todos los modelos de dominio para que Beanie los inicialice

from app.domains.error_logs import ErrorLog
from app.domains.auth import AuthSession
from app.domains.users import User
from app.domains.bussines import Business
from app.domains.category import Category
from app.domains.products import Product
from app.domains.meta import Meta
all_models = [
    ErrorLog,
    User,
    Business,
    Category,
    Product,
    Meta,
    AuthSession,
]
