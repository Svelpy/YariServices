"""
Tests unitarios para el modelo User.
Tipo: Unit — Sin I/O ni interacción con base de datos.
"""
from app.shared.enums import Role
from app.domains.users import User


class TestUserModelRepresentation:
    """Tests para los métodos mágicos __repr__ y __str__ de User."""

    def test_str_devuelve_email(self):
        user = User.model_construct(email="test@example.com")
        assert str(user) == "test@example.com"

    def test_repr_devuelve_formato_correcto(self):
        user = User.model_construct(email="admin@example.com", role=Role.ADMIN)
        assert repr(user) == f"<User admin@example.com ({Role.ADMIN})>"
