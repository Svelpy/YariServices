# solo reexportamos todos los modelos de dominio para que Beanie los inicialice

from app.domains.error_logs import ErrorLog
from app.domains.auth import AuthSession, EmailVerificationToken
from app.domains.users import User
from app.domains.stores import Store
from app.domains.category import Category
from app.domains.products import Product
from app.domains.meta import Meta
from app.domains.billing import Invoice, Payment, Plan, Subscription
all_models = [
    ErrorLog,
    User,
    Store,
    Category,
    Product,
    Meta,
    Plan,
    Subscription,
    Invoice,
    Payment,
    AuthSession,
    EmailVerificationToken,
]
