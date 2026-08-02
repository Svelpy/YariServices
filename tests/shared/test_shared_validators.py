import pytest

from app.shared.services.validators import (
    validator_names,
    validator_password,
    validator_phone,
    validator_username,
)


class TestValidatorNames:
    """Tests para validator_names."""

    def test_nombre_valido(self):
        assert validator_names("Juan Pérez") == "Juan Pérez"

    def test_nombre_con_tildes(self):
        assert validator_names("María José") == "María José"

    def test_nombre_con_apostrofe(self):
        assert validator_names("O'Brien") == "O'Brien"

    def test_nombre_con_guion(self):
        assert validator_names("Ana-Lucía") == "Ana-Lucía"

    def test_none_retorna_none(self):
        assert validator_names(None) is None

    def test_espacios_al_inicio_y_final_se_eliminan(self):
        assert validator_names("  Juan  ") == "Juan"

    def test_con_numeros_lanza_error(self):
        with pytest.raises(ValueError, match="Solo se permiten letras"):
            validator_names("Juan123")

    def test_con_caracteres_especiales_lanza_error(self):
        with pytest.raises(ValueError, match="Solo se permiten letras"):
            validator_names("Juan@Perez")

    def test_con_puntuacion_lanza_error(self):
        with pytest.raises(ValueError, match="Solo se permiten letras"):
            validator_names("Juan.Perez")


class TestValidatorUsername:
    """Tests para validator_username."""

    def test_username_valido(self):
        assert validator_username("usuario_123") == "usuario_123"

    def test_none_retorna_none(self):
        assert validator_username(None) is None

    def test_mayusculas_convertidas_a_minusculas(self):
        assert validator_username("UsuarioTest") == "usuariotest"

    def test_espacios_eliminados(self):
        assert validator_username("  usuario  ") == "usuario"

    def test_empieza_con_guion_lanza_error(self):
        with pytest.raises(ValueError, match="no puede empezar"):
            validator_username("-usuario")

    def test_empieza_con_guion_bajo_lanza_error(self):
        with pytest.raises(ValueError, match="no puede empezar"):
            validator_username("_usuario")

    def test_termina_con_guion_lanza_error(self):
        with pytest.raises(ValueError, match="no puede empezar"):
            validator_username("usuario-")

    def test_termina_con_guion_bajo_lanza_error(self):
        with pytest.raises(ValueError, match="no puede empezar"):
            validator_username("usuario_")

    def test_guiones_consecutivos_lanza_error(self):
        with pytest.raises(ValueError, match="consecutivos"):
            validator_username("usuario--test")

    def test_guiones_bajos_consecutivos_lanza_error(self):
        with pytest.raises(ValueError, match="consecutivos"):
            validator_username("usuario__test")

    def test_guion_guion_bajo_consecutivos_lanza_error(self):
        with pytest.raises(ValueError, match="consecutivos"):
            validator_username("usuario-_test")

    def test_caracter_arroba_lanza_error(self):
        with pytest.raises(ValueError, match="solo puede contener"):
            validator_username("user@name")

    def test_caracter_punto_lanza_error(self):
        with pytest.raises(ValueError, match="solo puede contener"):
            validator_username("user.name")

    def test_username_solo_numeros_valido(self):
        assert validator_username("123456") == "123456"

    def test_username_con_guion_medio_valido(self):
        assert validator_username("my-user") == "my-user"


class TestValidatorPassword:
    """Tests para validator_password (restricciones comentadas)."""

    def test_password_simple_se_retorna_igual(self):
        assert validator_password("abc") == "abc"

    def test_password_solo_minusculas(self):
        assert validator_password("password") == "password"

    def test_password_solo_numeros(self):
        assert validator_password("12345678") == "12345678"

    def test_password_sin_mayusculas_valido(self):
        assert validator_password("sinmayusculas1") == "sinmayusculas1"

    def test_password_vacio(self):
        assert validator_password("") == ""


class TestValidatorPhone:
    """Tests para validator_phone."""

    def test_telefono_valido(self):
        assert validator_phone("+1234567890") == "+1234567890"

    def test_telefono_limite_minimo(self):
        assert validator_phone("+12345") == "+12345"

    def test_telefono_limite_maximo(self):
        assert validator_phone("+123456789012345") == "+123456789012345"

    def test_none_retorna_none(self):
        assert validator_phone(None) is None

    def test_sin_mas_lanza_error(self):
        with pytest.raises(ValueError, match="debe tener entre"):
            validator_phone("1234567890")

    def test_muy_corto_lanza_error(self):
        with pytest.raises(ValueError, match="debe tener entre"):
            validator_phone("+1234")

    def test_muy_largo_lanza_error(self):
        with pytest.raises(ValueError, match="debe tener entre"):
            validator_phone("+1234567890123456")

    def test_con_letras_lanza_error(self):
        with pytest.raises(ValueError, match="debe tener entre"):
            validator_phone("+123abc456")

    def test_con_espacios_lanza_error(self):
        with pytest.raises(ValueError, match="debe tener entre"):
            validator_phone("+123 456 7890")
