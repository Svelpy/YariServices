from datetime import timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestHashPassword:
    """Tests para hash_password."""

    def test_devuelve_hash_distinto_al_texto_plano(self):
        hashed = hash_password("mi_password")
        assert hashed != "mi_password"

    def test_hashes_distintos_para_mismo_input(self):
        """Bcrypt genera salt aleatorio: dos hashes del mismo texto son diferentes."""
        hashed1 = hash_password("mismo_password")
        hashed2 = hash_password("mismo_password")
        assert hashed1 != hashed2

    def test_hash_es_string(self):
        hashed = hash_password("cualquier_cosa")
        assert isinstance(hashed, str)

    def test_hash_no_esta_vacio(self):
        hashed = hash_password("password")
        assert len(hashed) > 0


class TestVerifyPassword:
    """Tests para verify_password."""

    def test_contrasena_correcta_retorna_true(self):
        password = "mi_password_seguro"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_contrasena_incorrecta_retorna_false(self):
        hashed = hash_password("password_correcto")
        assert verify_password("password_incorrecto", hashed) is False

    def test_contrasena_vacia_correcta(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_contrasena_vacia_incorrecta(self):
        hashed = hash_password("no_vacia")
        assert verify_password("", hashed) is False

    def test_contrasena_larga(self):
        """SHA-256 pre-hash evita el límite de 72 bytes de Bcrypt."""
        long_password = "a" * 200
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True

    def test_password_diferente_longitud(self):
        hashed = hash_password("password123")
        assert verify_password("password12", hashed) is False


class TestCreateAccessToken:
    """Tests para create_access_token."""

    def test_devuelve_string_jwt(self):
        token = create_access_token({"sub": "user_id_123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_con_expires_delta_personalizado(self):
        delta = timedelta(minutes=30)
        token = create_access_token({"sub": "user_id"}, expires_delta=delta)
        assert isinstance(token, str)

    def test_payload_contiene_datos_originales(self):
        data = {"sub": "abc123", "email": "test@test.com", "role": "USER"}
        token = create_access_token(data)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "abc123"
        assert payload["email"] == "test@test.com"
        assert payload["role"] == "USER"

    def test_payload_contiene_campo_exp(self):
        token = create_access_token({"sub": "user"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_sin_expires_delta_usa_settings(self):
        """Sin expires_delta, el token usa ACCESS_TOKEN_EXPIRE_MINUTES de settings."""
        token = create_access_token({"sub": "user"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload


class TestDecodeAccessToken:
    """Tests para decode_access_token."""

    def test_token_valido_devuelve_payload(self):
        data = {"sub": "user_xyz", "role": "ADMIN"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user_xyz"
        assert payload["role"] == "ADMIN"

    def test_token_manipulado_devuelve_none(self):
        token = create_access_token({"sub": "user"})
        token_manipulado = token + "manipulado"
        result = decode_access_token(token_manipulado)
        assert result is None

    def test_token_invalido_devuelve_none(self):
        result = decode_access_token("esto.no.es.un.jwt")
        assert result is None

    def test_string_vacio_devuelve_none(self):
        result = decode_access_token("")
        assert result is None

    def test_token_expirado_devuelve_none(self):
        token = create_access_token(
            {"sub": "user"},
            expires_delta=timedelta(seconds=-1),
        )
        result = decode_access_token(token)
        assert result is None

    def test_token_con_clave_incorrecta_devuelve_none(self):
        token_falso = jwt.encode(
            {"sub": "hacker"},
            "clave_incorrecta",
            algorithm=settings.ALGORITHM,
        )
        result = decode_access_token(token_falso)
        assert result is None
