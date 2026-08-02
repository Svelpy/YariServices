from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación usando variables de entorno"""
    
    # App
    APP_NAME: str = "Proyect_Service_API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = """Lorep Ipsum"""
    DEBUG: bool = False

    
    # MongoDB Atlas
    MONGODB_URL: str = None
    MONGODB_DB_NAME: str = None
    TEST_MONGODB_DB_NAME: str = None
    # JWT Authentication
    SECRET_KEY: str = None
    ALGORITHM: str = None
    ACCESS_TOKEN_EXPIRE_MINUTES_DEV: int = 1440  # 1 día para desarrollo
    ACCESS_TOKEN_EXPIRE_MINUTES_PROD: int = 180    # 3 horas para producción
    
    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        """
        Retorna el tiempo de expiración del token según el modo DEBUG

        """
        if self.DEBUG:
            return self.ACCESS_TOKEN_EXPIRE_MINUTES_DEV
        return self.ACCESS_TOKEN_EXPIRE_MINUTES_PROD
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = None
    CLOUDINARY_API_KEY: str = None
    CLOUDINARY_API_SECRET: str = None
    CLOUDINARY_FOLDER_NAME: str = None
    
    # CORS — Orígenes de desarrollo (DEBUG=True)
    DEV_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    # CORS — Orígenes de producción (DEBUG=False)
    PROD_ORIGINS: str = None

    @property
    def CORS_ORIGINS_LIST(self) -> list:
        """
        Retorna la lista de orígenes CORS según el modo:

        """
        if self.DEBUG:
            return [o.strip() for o in self.DEV_ORIGINS.split(",") if o.strip()]

        return [o.strip() for o in self.PROD_ORIGINS.split(",") if o.strip()]
    # Seeds
    SEED_ADMIN_EMAIL_1: str = "superadmin1@example.com"
    SEED_ADMIN_NAME_1: str = "Super"
    SEED_ADMIN_LASTNAME_1: str = "Admin Uno"
    SEED_ADMIN_USERNAME_1: str = "superadmin1"
    SEED_ADMIN_PASSWORD_1: str = "SuperAdmin123"
    SEED_ADMIN_EMAIL_2: str = "superadmin2@example.com"
    SEED_ADMIN_NAME_2: str = "Super"
    SEED_ADMIN_LASTNAME_2: str = "Admin Dos"
    SEED_ADMIN_USERNAME_2: str = "superadmin2"
    SEED_ADMIN_PASSWORD_2: str = "SuperAdmin321"
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()
