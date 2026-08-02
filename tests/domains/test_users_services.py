"""
Tests unitarios para UserService.
Tipo: Unit — Mocks de User, CloudinaryService y hashing.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException
from app.domains.users import (
    AdminResetPassword,
    PasswordSelfUpdate,
    User,
    UserCreate,
    UserSelfUpdate,
    UserUpdate,
    UserService,
)


class TestUserServiceRegisterUser:
    """Tests para register_user"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    @patch("app.domains.users.services.hash_password")
    async def test_creacion_exitosa_por_actor_con_mayor_jerarquia(self, mock_hash, mock_user_cls):
        user_data = UserCreate(
            email="nuevo@example.com",
            password="Password123",
            role=Role.GERENTE
        )

        actor = MagicMock()
        actor.role = Role.ADMIN
        actor.id = PydanticObjectId("507f1f77bcf86cd799439011")

        mock_hash.return_value = "hashed_pwd"
        mock_user_cls.find_one = AsyncMock(return_value=None)

        mock_user_instance = MagicMock()
        mock_user_instance.save = AsyncMock()
        mock_user_cls.return_value = mock_user_instance

        result = await UserService.register_user(user_data, actor)

        assert result is mock_user_instance
        mock_user_instance.save.assert_called_once()
        mock_hash.assert_called_once_with("Password123")

    @pytest.mark.asyncio
    async def test_creacion_falla_por_jerarquia_insuficiente(self):
        user_data = UserCreate(
            email="nuevo@example.com",
            password="Password123",
            role=Role.ADMIN
        )
        actor = MagicMock()
        actor.role = Role.GERENTE

        with pytest.raises(AppException) as exc_info:
            await UserService.register_user(user_data, actor)

        assert exc_info.value.status_code == 403
        assert "No tienes permisos" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_email_duplicado_lanza_error(self, mock_user_cls):
        user_data = UserCreate(
            email="duplicado@example.com",
            password="Password123",
            role=Role.GERENTE
        )
        actor = MagicMock()
        actor.role = Role.ADMIN

        mock_user_cls.find_one = AsyncMock(return_value=MagicMock())

        with pytest.raises(AppException) as exc_info:
            await UserService.register_user(user_data, actor)

        assert exc_info.value.status_code == 409
        assert "email ya está registrado" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_username_duplicado_lanza_error(self, mock_user_cls):
        user_data = UserCreate(
            email="nuevo@example.com",
            username="duplicadouser",
            password="Password123",
            role=Role.GERENTE
        )
        actor = MagicMock()
        actor.role = Role.ADMIN

        mock_user_cls.find_one = AsyncMock(side_effect=[None, MagicMock()])

        with pytest.raises(AppException) as exc_info:
            await UserService.register_user(user_data, actor)

        assert exc_info.value.status_code == 409
        assert "username ya está en uso" in exc_info.value.message


class TestUserServiceListUsers:
    """Tests para list_users"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_listar_usuarios_sin_filtros(self, mock_user_cls):
        mock_query = MagicMock()
        mock_query.find.return_value = mock_query
        mock_query.count = AsyncMock(return_value=5)

        mock_query.sort.return_value = mock_query
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_users_list = [MagicMock(), MagicMock()]
        mock_query.to_list = AsyncMock(return_value=mock_users_list)

        mock_user_cls.find.return_value = mock_query

        result = await UserService.list_users(page=1, per_page=10)

        assert result["total"] == 5
        assert result["total_pages"] == 1
        assert result["data"] == mock_users_list

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_listar_usuarios_con_busqueda_y_filtros(self, mock_user_cls):
        mock_query = MagicMock()
        mock_query.find.return_value = mock_query
        mock_query.count = AsyncMock(return_value=1)

        mock_query.sort.return_value = mock_query
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_users_list = [MagicMock()]
        mock_query.to_list = AsyncMock(return_value=mock_users_list)

        mock_user_cls.find.return_value = mock_query

        result = await UserService.list_users(
            page=1, per_page=10, q="carlos", role=Role.USER, user_status=UserStatus.ACTIVE
        )

        assert result["total"] == 1
        assert result["data"] == mock_users_list


class TestUserServiceGetUser:
    """Tests para get_user y _get_active_user"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_get_user_exitoso(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_user = MagicMock()
        mock_user.is_deleted = False
        mock_user_cls.get = AsyncMock(return_value=mock_user)

        result = await UserService.get_user(user_id)
        assert result is mock_user

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_get_user_inexistente_lanza_404(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_user_cls.get = AsyncMock(return_value=None)

        with pytest.raises(AppException) as exc_info:
            await UserService.get_user(user_id)

        assert exc_info.value.status_code == 404
        assert "no existente" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_get_user_eliminado_lanza_404(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_user = MagicMock()
        mock_user.is_deleted = True
        mock_user_cls.get = AsyncMock(return_value=mock_user)

        with pytest.raises(AppException) as exc_info:
            await UserService.get_user(user_id)

        assert exc_info.value.status_code == 404
        assert "eliminado" in exc_info.value.message


class TestUserServiceUpdateUser:
    """Tests para update_user"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_update_exitoso(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")

        target_user = MagicMock()
        target_user.role = Role.GERENTE
        target_user.is_deleted = False
        target_user.username = "viejousername"
        target_user.email = "viejoemail@example.com"
        target_user.save = AsyncMock()

        actor = MagicMock()
        actor.role = Role.ADMIN
        actor.id = PydanticObjectId("507f1f77bcf86cd799439022")

        mock_user_cls.get = AsyncMock(return_value=target_user)
        mock_user_cls.find_one = AsyncMock(return_value=None)

        update_data = UserUpdate(username="nuevousername", email="nuevoemail@example.com")

        result = await UserService.update_user(user_id, update_data, actor)

        assert result.username == "nuevousername"
        assert result.email == "nuevoemail@example.com"
        assert result.updated_by == actor.id
        target_user.save.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_update_mismo_rango_lanza_403(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        target_user = MagicMock()
        target_user.role = Role.ADMIN
        target_user.is_deleted = False

        actor = MagicMock()
        actor.role = Role.ADMIN

        mock_user_cls.get = AsyncMock(return_value=target_user)

        with pytest.raises(AppException) as exc:
            await UserService.update_user(user_id, UserUpdate(name="Juan"), actor)

        assert exc.value.status_code == 403


class TestUserServiceUpdateAvatar:
    """Tests para update_avatar y update_avatar_self"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    @patch("app.domains.users.services.CloudinaryService")
    async def test_update_avatar_administrativo_exitoso(self, mock_cloudinary, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")

        target_user = MagicMock()
        target_user.role = Role.GERENTE
        target_user.is_deleted = False
        target_user.avatar_url = "https://cloudinary.com/old.jpg"
        target_user.save = AsyncMock()

        actor = MagicMock()
        actor.role = Role.ADMIN
        actor.id = PydanticObjectId("507f1f77bcf86cd799439022")

        mock_user_cls.get = AsyncMock(return_value=target_user)
        mock_cloudinary.upload_image = AsyncMock(return_value="https://cloudinary.com/new.jpg")
        mock_cloudinary.delete_image = AsyncMock()

        file = MagicMock()
        result = await UserService.update_avatar(user_id, file, actor)

        assert result.avatar_url == "https://cloudinary.com/new.jpg"
        mock_cloudinary.upload_image.assert_called_once_with(file, folder="avatars")
        mock_cloudinary.delete_image.assert_called_once_with("https://cloudinary.com/old.jpg")
        target_user.save.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.users.services.CloudinaryService")
    async def test_update_avatar_self_exitoso(self, mock_cloudinary):
        actor = MagicMock()
        actor.avatar_url = "https://cloudinary.com/old_self.jpg"
        actor.id = PydanticObjectId("507f1f77bcf86cd799439011")
        actor.save = AsyncMock()

        mock_cloudinary.upload_image = AsyncMock(return_value="https://cloudinary.com/new_self.jpg")
        mock_cloudinary.delete_image = AsyncMock()

        file = MagicMock()
        result = await UserService.update_avatar_self(file, actor)

        assert result.avatar_url == "https://cloudinary.com/new_self.jpg"
        mock_cloudinary.upload_image.assert_called_once_with(file, folder="avatars")
        mock_cloudinary.delete_image.assert_called_once_with("https://cloudinary.com/old_self.jpg")
        actor.save.assert_called_once()


class TestUserServiceResetPassword:
    """Tests para reset_password"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    @patch("app.domains.users.services.hash_password")
    async def test_reset_password_exitoso(self, mock_hash, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")

        target_user = MagicMock()
        target_user.role = Role.GERENTE
        target_user.is_deleted = False
        target_user.save = AsyncMock()

        actor = MagicMock()
        actor.role = Role.ADMIN
        actor.id = PydanticObjectId("507f1f77bcf86cd799439022")

        mock_user_cls.get = AsyncMock(return_value=target_user)
        mock_hash.return_value = "new_hashed_pwd"

        data = AdminResetPassword(new_password="NuevaPassword123")

        await UserService.reset_password(user_id, data, actor)

        assert target_user.password_hash == "new_hashed_pwd"
        target_user.save.assert_called_once()
        mock_hash.assert_called_once_with("NuevaPassword123")


class TestUserServiceDeleteUser:
    """Tests para delete_user (Soft vs Hard delete)"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_soft_delete_por_admin(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")

        target_user = MagicMock()
        target_user.role = Role.GERENTE
        target_user.is_deleted = False
        target_user.save = AsyncMock()

        actor = MagicMock()
        actor.role = Role.ADMIN
        actor.id = PydanticObjectId("507f1f77bcf86cd799439022")

        mock_user_cls.get = AsyncMock(return_value=target_user)

        await UserService.delete_user(user_id, actor, hard_delete=False)

        assert target_user.is_deleted is True
        assert target_user.deleted_by == actor.id
        target_user.save.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_hard_delete_por_superadmin(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")

        target_user = MagicMock()
        target_user.role = Role.GERENTE
        target_user.is_deleted = False
        target_user.delete = AsyncMock()

        actor = MagicMock()
        actor.role = Role.SUPERADMIN

        mock_user_cls.get = AsyncMock(return_value=target_user)

        await UserService.delete_user(user_id, actor, hard_delete=True)

        target_user.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_hard_delete_por_admin_falla_con_403(self, mock_user_cls):
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        actor = MagicMock()
        actor.role = Role.ADMIN

        with pytest.raises(AppException) as exc:
            await UserService.delete_user(user_id, actor, hard_delete=True)

        assert exc.value.status_code == 403
        assert "SUPERADMIN" in exc.value.message


class TestUserServiceSelfManagement:
    """Tests para operaciones propias del actor (autogestión)"""

    @pytest.mark.asyncio
    @patch("app.domains.users.services.User")
    async def test_update_profile_exitoso(self, mock_user_cls):
        actor = MagicMock()
        actor.username = "viejo"
        actor.id = PydanticObjectId("507f1f77bcf86cd799439011")
        actor.save = AsyncMock()

        mock_user_cls.find_one = AsyncMock(return_value=None)

        update_data = UserSelfUpdate(username="nuevo")
        result = await UserService.update_profile(update_data, actor)

        assert result.username == "nuevo"
        assert result.updated_by == actor.id
        actor.save.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.users.services.verify_password")
    @patch("app.domains.users.services.hash_password")
    async def test_change_password_exitoso(self, mock_hash, mock_verify):
        actor = MagicMock()
        actor.password_hash = "hashed_old"
        actor.save = AsyncMock()

        mock_verify.return_value = True
        mock_hash.return_value = "hashed_new"

        data = PasswordSelfUpdate(
            current_password="old_password",
            new_password="new_password"
        )

        await UserService.change_password(actor, data)

        assert actor.password_hash == "hashed_new"
        actor.save.assert_called_once()
        mock_verify.assert_called_once_with("old_password", "hashed_old")
        mock_hash.assert_called_once_with("new_password")

    @pytest.mark.asyncio
    @patch("app.domains.users.services.verify_password")
    async def test_change_password_incorrecta_lanza_401(self, mock_verify):
        actor = MagicMock()
        actor.password_hash = "hashed_old"

        mock_verify.return_value = False

        data = PasswordSelfUpdate(
            current_password="wrong_password",
            new_password="new_password"
        )

        with pytest.raises(AppException) as exc_info:
            await UserService.change_password(actor, data)

        assert exc_info.value.status_code == 401
        assert "incorrecta" in exc_info.value.message
