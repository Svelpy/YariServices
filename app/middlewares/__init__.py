from fastapi import FastAPI

from app.middlewares.cors import register_cors
from app.middlewares.exception_handlers import register_exception_handlers
from app.middlewares.limiter import register_rate_limiter
from app.core.config import Settings


def register_all_middlewares(app: FastAPI, settings: Settings) -> None:
    """
    Registra todos los middlewares globales de la aplicación.
    El orden importa: los middlewares se ejecutan en orden inverso al de registro.
    """
    register_rate_limiter(app)
    register_exception_handlers(app,settings)
    register_cors(app,settings)
