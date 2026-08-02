from fastapi import FastAPI

from app.middlewares.cors import register_cors
from app.middlewares.exception_handlers import register_exception_handlers
from app.middlewares.limiter import register_rate_limiter


def register_all_middlewares(app: FastAPI) -> None:
    """
    Registra todos los middlewares globales de la aplicación.
    El orden importa: los middlewares se ejecutan en orden inverso al de registro.
    """
    register_rate_limiter(app)
    register_exception_handlers(app)
    register_cors(app)
