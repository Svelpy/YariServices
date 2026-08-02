import pytest

from app.shared.services.slug import generate_slug


class TestGenerateSlug:
    """Tests para generate_slug."""

    def test_texto_simple(self):
        assert generate_slug("Hola Mundo") == "hola-mundo"

    def test_tildes_normalizadas(self):
        assert generate_slug("café") == "cafe"
        assert generate_slug("niño") == "nino"
        assert generate_slug("corazón") == "corazon"

    def test_mayusculas_a_minusculas(self):
        assert generate_slug("PYTHON ES GENIAL") == "python-es-genial"

    def test_caracteres_especiales_reemplazados(self):
        assert generate_slug("hello@world!") == "hello-world"
        assert generate_slug("precio: $100") == "precio-100"

    def test_guiones_al_inicio_y_final_eliminados(self):
        assert generate_slug("---hola---") == "hola"
        assert generate_slug("  hola  ") == "hola"

    def test_multiples_espacios_consecutivos(self):
        assert generate_slug("hola   mundo") == "hola-mundo"

    def test_multiples_guiones_consecutivos(self):
        assert generate_slug("a---b") == "a-b"

    def test_texto_vacio(self):
        assert generate_slug("") == ""

    def test_solo_caracteres_especiales(self):
        assert generate_slug("!!!") == ""

    def test_numeros_en_texto(self):
        assert generate_slug("producto 123") == "producto-123"

    def test_mezcla_acentos_y_especiales(self):
        assert generate_slug("¡Árbol de navidad!") == "arbol-de-navidad"
