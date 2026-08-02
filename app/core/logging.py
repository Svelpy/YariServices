import logging

from app.core.config import settings


def setup_logging() -> None:
    """
    Configura el sistema de logging global.
    """
    logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.WARNING,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Devuelve un logger identificado por nombre.
    Uso: logger = get_logger(__name__)
    """
    return logging.getLogger(name)