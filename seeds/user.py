import asyncio
import logging
from pathlib import Path

from beanie import init_beanie
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import AsyncMongoClient

from app.core.security import hash_password
from app.domains import all_models
from app.domains.users import User
from app.shared.enums import Role, UserStatus


class SeedSettings(BaseSettings):
    """Configuración exclusiva para ejecutar los seeds."""

    MONGODB_URL: str
    MONGODB_DB_NAME: str

    SEED_ADMIN_EMAIL_1: str
    SEED_ADMIN_NAME_1: str
    SEED_ADMIN_LASTNAME_1: str
    SEED_ADMIN_USERNAME_1: str
    SEED_ADMIN_PASSWORD_1: str

    SEED_ADMIN_EMAIL_2: str
    SEED_ADMIN_NAME_2: str
    SEED_ADMIN_LASTNAME_2: str
    SEED_ADMIN_USERNAME_2: str
    SEED_ADMIN_PASSWORD_2: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def seed_users(settings: SeedSettings) -> None:
    """Crea los usuarios iniciales si la colección está vacía."""

    mongodb_client = AsyncMongoClient(
        settings.MONGODB_URL,
        tz_aware=True,
    )
    database = mongodb_client.get_database(settings.MONGODB_DB_NAME)

    try:
        await database.command("ping")

        await init_beanie(
            database=database,
            document_models=all_models,
        )

        user_count = await User.count()

        if user_count > 0:
            logger.info(
                "La base de datos ya contiene %s usuarios. "
                "Se omite la carga inicial.",
                user_count,
            )
            return

        admin1 = User(
            email=settings.SEED_ADMIN_EMAIL_1,
            name=settings.SEED_ADMIN_NAME_1,
            lastname=settings.SEED_ADMIN_LASTNAME_1,
            username=settings.SEED_ADMIN_USERNAME_1,
            password_hash=hash_password(settings.SEED_ADMIN_PASSWORD_1),
            role=Role.SUPERADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True,
        )

        admin2 = User(
            email=settings.SEED_ADMIN_EMAIL_2,
            name=settings.SEED_ADMIN_NAME_2,
            lastname=settings.SEED_ADMIN_LASTNAME_2,
            username=settings.SEED_ADMIN_USERNAME_2,
            password_hash=hash_password(settings.SEED_ADMIN_PASSWORD_2),
            role=Role.SUPERADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True,
        )

        await admin1.insert()
        await admin2.insert()

        logger.info(
            "Se cargaron exitosamente 2 usuarios SUPERADMIN."
        )

    except Exception:
        logger.exception("Error durante la ejecución del seed")
        raise

    finally:
        await mongodb_client.close()


if __name__ == "__main__":
    asyncio.run(seed_users(SeedSettings()))