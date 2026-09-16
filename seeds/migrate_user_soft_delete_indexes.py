import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import ASCENDING, AsyncMongoClient, IndexModel


class MigrationSettings(BaseSettings):
    """Configuración mínima para migrar los índices de usuarios."""

    ENVIRONMENT: str = "development"
    MONGODB_URL: str
    MONGODB_DB_NAME: str

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


INDEX_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "email_1",
        "keys": [("email", ASCENDING)],
        "partial_filter": {"is_deleted": False},
    },
    {
        "name": "username_1",
        "keys": [("username", ASCENDING)],
        "partial_filter": {
            "username": {"$type": "string"},
            "is_deleted": False,
        },
    },
    {
        "name": "auth_provider_1_provider_user_id_1",
        "keys": [
            ("auth_provider", ASCENDING),
            ("provider_user_id", ASCENDING),
        ],
        "partial_filter": {
            "provider_user_id": {"$type": "string"},
            "is_deleted": False,
        },
    },
)


def _matches_definition(
    index_data: dict[str, Any],
    definition: dict[str, Any],
) -> bool:
    return (
        list(index_data.get("key", [])) == definition["keys"]
        and index_data.get("unique") is True
        and index_data.get("partialFilterExpression")
        == definition["partial_filter"]
    )


async def migrate_user_indexes(
    settings: MigrationSettings,
    allow_non_development: bool = False,
) -> None:
    if settings.ENVIRONMENT != "development" and not allow_non_development:
        raise RuntimeError(
            "La migración solo se ejecuta en development. "
            "Usa --allow-non-development para autorizar otro entorno."
        )

    mongodb_client = AsyncMongoClient(settings.MONGODB_URL, tz_aware=True)
    database = mongodb_client.get_database(settings.MONGODB_DB_NAME)
    users = database.get_collection("users")

    try:
        await database.command("ping")
        logger.info(
            "Migrando índices de users en base '%s' (%s).",
            settings.MONGODB_DB_NAME,
            settings.ENVIRONMENT,
        )

        backfill_result = await users.update_many(
            {"is_deleted": {"$exists": False}},
            {"$set": {"is_deleted": False}},
        )
        logger.info(
            "Backfill is_deleted: %s documentos actualizados.",
            backfill_result.modified_count,
        )

        current_indexes = await users.index_information()

        for definition in INDEX_DEFINITIONS:
            for index_name, index_data in list(current_indexes.items()):
                if list(index_data.get("key", [])) != definition["keys"]:
                    continue
                if _matches_definition(index_data, definition):
                    continue

                logger.info("Eliminando índice incompatible '%s'.", index_name)
                await users.drop_index(index_name)
                current_indexes.pop(index_name, None)

        requested_indexes = [
            IndexModel(
                definition["keys"],
                name=definition["name"],
                unique=True,
                partialFilterExpression=definition["partial_filter"],
            )
            for definition in INDEX_DEFINITIONS
        ]
        await users.create_indexes(requested_indexes)

        migrated_indexes = await users.index_information()
        invalid_indexes = [
            definition["name"]
            for definition in INDEX_DEFINITIONS
            if definition["name"] not in migrated_indexes
            or not _matches_definition(
                migrated_indexes[definition["name"]],
                definition,
            )
        ]
        if invalid_indexes:
            raise RuntimeError(
                "No se pudieron validar los índices: "
                + ", ".join(invalid_indexes)
            )

        logger.info(
            "Migración verificada: email, username y proveedor externo "
            "son únicos solo para usuarios no eliminados."
        )
    finally:
        await mongodb_client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra los índices únicos parciales de users.",
    )
    parser.add_argument(
        "--allow-non-development",
        action="store_true",
        help="Autoriza explícitamente ejecutar fuera de development.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(
        migrate_user_indexes(
            MigrationSettings(),
            allow_non_development=arguments.allow_non_development,
        )
    )
