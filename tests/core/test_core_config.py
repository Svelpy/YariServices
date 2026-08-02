import pytest
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings


# Subclase aislada del .env: provee defaults vacíos para campos obligatorios
# que en producción se cargan desde el archivo .env real.
class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(env_file=None, case_sensitive=True)

    MONGODB_URL: str = "mongodb://localhost"
    MONGODB_DB_NAME: str = "test_db"
    TEST_MONGODB_DB_NAME: str = "test_db_test"
    SECRET_KEY: str = "test_secret_key_32chars_minimo__"
    ALGORITHM: str = "HS256"
    CLOUDINARY_CLOUD_NAME: str = "test_cloud"
    CLOUDINARY_API_KEY: str = "test_api_key"
    CLOUDINARY_API_SECRET: str = "test_api_secret"
    CLOUDINARY_FOLDER_NAME: str = "test_folder"
    PROD_ORIGINS: str = "https://test.com"


class TestSettingsDefaults:
    """Tests para valores por defecto de Settings (sin .env)."""

    def _make(self, **kwargs) -> IsolatedSettings:
        base = dict(
            MONGODB_URL="mongodb://localhost",
            MONGODB_DB_NAME="test_db",
            SECRET_KEY="clave_secreta_test_32chars_minimo",
            ALGORITHM="HS256",
        )
        base.update(kwargs)
        return IsolatedSettings(**base)

    def test_app_name_por_defecto(self):
        s = self._make()
        assert s.APP_NAME == "Proyect_Service_API"

    def test_app_version_por_defecto(self):
        s = self._make()
        assert s.APP_VERSION == "1.0.0"

    def test_debug_false_por_defecto(self):
        s = self._make()
        assert s.DEBUG is False


class TestAccessTokenExpireMinutes:
    """Tests para la property ACCESS_TOKEN_EXPIRE_MINUTES."""

    def _make(self, **kwargs) -> IsolatedSettings:
        base = dict(
            MONGODB_URL="mongodb://localhost",
            MONGODB_DB_NAME="test_db",
            SECRET_KEY="clave_secreta_test_32chars_minimo",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES_DEV=1440,
            ACCESS_TOKEN_EXPIRE_MINUTES_PROD=180,
        )
        base.update(kwargs)
        return IsolatedSettings(**base)

    def test_debug_true_devuelve_expire_dev(self):
        s = self._make(DEBUG=True)
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 1440

    def test_debug_false_devuelve_expire_prod(self):
        s = self._make(DEBUG=False)
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 180

    def test_valores_personalizados_dev(self):
        s = self._make(
            DEBUG=True,
            ACCESS_TOKEN_EXPIRE_MINUTES_DEV=720,
            ACCESS_TOKEN_EXPIRE_MINUTES_PROD=60,
        )
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 720

    def test_valores_personalizados_prod(self):
        s = self._make(
            DEBUG=False,
            ACCESS_TOKEN_EXPIRE_MINUTES_DEV=720,
            ACCESS_TOKEN_EXPIRE_MINUTES_PROD=60,
        )
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60


class TestCorsOriginsList:
    """Tests para la property CORS_ORIGINS_LIST."""

    def _make(self, **kwargs) -> IsolatedSettings:
        base = dict(
            MONGODB_URL="mongodb://localhost",
            MONGODB_DB_NAME="test_db",
            SECRET_KEY="clave_secreta_test_32chars_minimo",
            ALGORITHM="HS256",
        )
        base.update(kwargs)
        return IsolatedSettings(**base)

    def test_debug_true_devuelve_origenes_dev(self):
        s = self._make(
            DEBUG=True,
            DEV_ORIGINS="http://localhost:5173,http://localhost:5174",
            PROD_ORIGINS="https://produccion.com",
        )
        origins = s.CORS_ORIGINS_LIST
        assert "http://localhost:5173" in origins
        assert "http://localhost:5174" in origins
        assert "https://produccion.com" not in origins

    def test_debug_false_devuelve_origenes_prod(self):
        s = self._make(
            DEBUG=False,
            DEV_ORIGINS="http://localhost:5173",
            PROD_ORIGINS="https://produccion.com,https://www.produccion.com",
        )
        origins = s.CORS_ORIGINS_LIST
        assert "https://produccion.com" in origins
        assert "https://www.produccion.com" in origins
        assert "http://localhost:5173" not in origins

    def test_cors_lista_devuelve_lista(self):
        s = self._make(
            DEBUG=True,
            DEV_ORIGINS="http://localhost:5173",
        )
        assert isinstance(s.CORS_ORIGINS_LIST, list)

    def test_cors_elimina_espacios(self):
        s = self._make(
            DEBUG=True,
            DEV_ORIGINS="  http://localhost:5173  ,  http://localhost:5174  ",
        )
        origins = s.CORS_ORIGINS_LIST
        assert "http://localhost:5173" in origins
        assert "http://localhost:5174" in origins
