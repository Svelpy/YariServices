from app.core.config import settings
import asyncio
import logging
from app.core.database import connect_to_mongo, close_mongo_connection
from app.domains.users import User
from app.shared.enums import Role, UserStatus
from app.core.security import hash_password

# Configurar logging básico para ver el output del script
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def seed_users():
    try:
        # 1. Conectar a MongoDB e inicializar Beanie<
        await connect_to_mongo()
        
        # 2. Verificar si la colección de usuarios está vacía
        user_count = await User.count()
        if user_count > 0:
            logger.info(f"La base de datos ya contiene {user_count} usuarios. Se omite la carga inicial.")
            return

        logger.info("La colección de usuarios está vacía. Procediendo a cargar usuarios iniciales...")

        admin1 = User(
            email=settings.SEED_ADMIN_EMAIL_1,
            name=settings.SEED_ADMIN_NAME_1,
            lastname=settings.SEED_ADMIN_LASTNAME_1,
            username=settings.SEED_ADMIN_USERNAME_1,
            password_hash=hash_password(settings.SEED_ADMIN_PASSWORD_1),
            role=Role.SUPERADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True
        )
        admin2 = User(
            email=settings.SEED_ADMIN_EMAIL_2,
            name=settings.SEED_ADMIN_NAME_2,
            lastname=settings.SEED_ADMIN_LASTNAME_2,
            username=settings.SEED_ADMIN_USERNAME_2,
            password_hash=hash_password(settings.SEED_ADMIN_PASSWORD_2),
            role=Role.SUPERADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True
        )

        # 4. Guardar los usuarios en la base de datos
        await admin1.insert()
        await admin2.insert()

        logger.info("✅ Se han cargado exitosamente 2 usuarios con rol SUPERADMIN.")

    except Exception as e:
        logger.error(f"❌ Error durante la ejecución del seed: {e}")
    finally:
        # 5. Cerrar la conexión
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed_users())


#python -m app.seeds.user