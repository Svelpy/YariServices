from app.shared.enums import AuthProvider, Role, UserStatus


class TestRoleEnum:
    """Tests para el enum Role."""

    def test_valores_correctos(self):
        assert Role.SUPERADMIN == "SUPERADMIN"
        assert Role.ADMIN == "ADMIN"
        assert Role.PROPIETARIO == "PROPIETARIO"
        assert Role.GERENTE == "GERENTE"
        assert Role.FINANZAS == "FINANZAS"
        assert Role.VENDEDOR == "VENDEDOR"
        assert Role.ALMACEN == "ALMACEN"
        assert Role.USER == "USER"

    def test_es_str_enum(self):
        assert isinstance(Role.USER, str)

    def test_comparacion_con_string(self):
        assert Role.USER == "USER"
        assert Role.ADMIN == "ADMIN"

    def test_todos_los_roles_presentes(self):
        nombres = {r.name for r in Role}
        assert "SUPERADMIN" in nombres
        assert "ADMIN" in nombres
        assert "PROPIETARIO" in nombres
        assert "GERENTE" in nombres
        assert "FINANZAS" in nombres
        assert "VENDEDOR" in nombres
        assert "ALMACEN" in nombres
        assert "USER" in nombres


class TestAuthProviderEnum:
    """Tests para el enum AuthProvider."""

    def test_valores_correctos(self):
        assert AuthProvider.LOCAL == "LOCAL"
        assert AuthProvider.GOOGLE == "GOOGLE"
        assert AuthProvider.GITHUB == "GITHUB"
        assert AuthProvider.APPLE == "APPLE"

    def test_es_str_enum(self):
        assert isinstance(AuthProvider.LOCAL, str)

    def test_comparacion_con_string(self):
        assert AuthProvider.GOOGLE == "GOOGLE"

    def test_todos_los_providers_presentes(self):
        nombres = {p.name for p in AuthProvider}
        assert "LOCAL" in nombres
        assert "GOOGLE" in nombres
        assert "GITHUB" in nombres
        assert "APPLE" in nombres


class TestUserStatusEnum:
    """Tests para el enum UserStatus."""

    def test_valores_correctos(self):
        assert UserStatus.PENDING_VERIFICATION == "PENDING_VERIFICATION"
        assert UserStatus.ACTIVE == "ACTIVE"
        assert UserStatus.INACTIVE == "INACTIVE"
        assert UserStatus.SUSPENDED == "SUSPENDED"
        assert UserStatus.BANNED == "BANNED"

    def test_es_str_enum(self):
        assert isinstance(UserStatus.ACTIVE, str)

    def test_comparacion_con_string(self):
        assert UserStatus.ACTIVE == "ACTIVE"
        assert UserStatus.BANNED == "BANNED"

    def test_todos_los_estados_presentes(self):
        nombres = {s.name for s in UserStatus}
        assert "PENDING_VERIFICATION" in nombres
        assert "ACTIVE" in nombres
        assert "INACTIVE" in nombres
        assert "SUSPENDED" in nombres
        assert "BANNED" in nombres
