"""
Tests pour les décorateurs de permissions.
"""

import pytest
from datetime import datetime, timedelta


class TestDecoratorImports:
    """Tests pour l'import des décorateurs."""

    def test_admin_required_import(self):
        """Test que le décorateur admin_required peut être importé."""
        from app.utils.decorators import admin_required

        assert callable(admin_required)

    def test_role_required_import(self):
        """Test que le décorateur role_required peut être importé."""
        from app.utils.decorators import role_required

        assert callable(role_required)

    def test_user_can_edit_import(self):
        """Test que le décorateur user_can_edit peut être importé."""
        from app.utils.decorators import user_can_edit

        assert callable(user_can_edit)

    def test_user_can_delete_import(self):
        """Test que le décorateur user_can_delete peut être importé."""
        from app.utils.decorators import user_can_delete

        assert callable(user_can_delete)

    def test_user_owns_resource_import(self):
        """Test que le décorateur user_owns_resource peut être importé."""
        from app.utils.decorators import user_owns_resource

        assert callable(user_owns_resource)

    def test_user_can_edit_resource_import(self):
        """Test que le décorateur user_can_edit_resource peut être importé."""
        from app.utils.decorators import user_can_edit_resource

        assert callable(user_can_edit_resource)

    def test_user_can_delete_resource_import(self):
        """Test que le décorateur user_can_delete_resource peut être importé."""
        from app.utils.decorators import user_can_delete_resource

        assert callable(user_can_delete_resource)


class TestDecoratorProperties:
    """Tests pour les propriétés des décorateurs."""

    def test_decorator_preserves_function_name(self, app):
        """Test que le décorateur préserve le nom de la fonction."""
        from app.utils.decorators import admin_required

        @admin_required
        def test_function():
            return "Test", 200

        assert test_function.__name__ == "test_function"

    def test_decorator_preserves_function_docstring(self, app):
        """Test que le décorateur préserve le docstring de la fonction."""
        from app.utils.decorators import admin_required

        @admin_required
        def test_function():
            """This is a test function."""
            return "Test", 200

        assert test_function.__doc__ == "This is a test function."

    def test_admin_required_is_callable(self, app):
        """Test que admin_required est callable."""
        from app.utils.decorators import admin_required

        @admin_required
        def dummy():
            pass

        assert callable(dummy)

    def test_role_required_is_callable(self, app):
        """Test que role_required est callable."""
        from app.utils.decorators import role_required

        decorated_func = role_required("admin")
        assert callable(decorated_func)

    def test_user_owns_resource_is_callable(self, app):
        """Test que user_owns_resource est callable."""
        from app.utils.decorators import user_owns_resource
        from app.models import Leave

        decorated_func = user_owns_resource(Leave, "leave_id")
        assert callable(decorated_func)


class TestAdminRequiredDecorator:
    """Tests pour le décorateur admin_required."""

    def test_admin_required_allows_admin(self, logged_in_admin_client):
        """Test qu'un admin peut accéder aux routes admin."""
        response = logged_in_admin_client.get("/admin")
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"admin" in response.data.lower()

    def test_admin_required_blocks_non_admin(self, logged_in_client):
        """Test qu'un utilisateur normal ne peut pas accéder aux routes admin."""
        response = logged_in_client.get("/admin", follow_redirects=True)
        assert response.status_code == 200
        # L'utilisateur est redirigé vers l'index
        assert b"Leviia" in response.data or b"Schedule" in response.data
        # Le message d'erreur devrait être présent
        assert (
            b"Acces refuse" in response.data
            or b"permissions" in response.data.lower()
            or b"admin" in response.data.lower()
        )


class TestRoleRequiredDecorator:
    """Tests pour le décorateur role_required."""

    def test_role_required_allows_user(self, logged_in_client):
        """Test qu'un utilisateur normal peut accéder aux routes user."""
        # La route index est accessible à tous les utilisateurs connectés
        response = logged_in_client.get("/")
        assert response.status_code == 200

    def test_role_required_allows_admin(self, logged_in_admin_client):
        """Test qu'un admin peut accéder aux routes user."""
        response = logged_in_admin_client.get("/")
        assert response.status_code == 200


class TestUserOwnsResourceDecorator:
    """Tests pour le décorateur user_owns_resource."""

    def test_user_can_delete_own_leave(
        self, logged_in_client, test_leave, test_user, app
    ):
        """Test qu'un utilisateur peut supprimer son propre congé."""
        # test_leave est déjà associé à test_user via la fixture
        # test_user est déjà connecté via logged_in_client
        response = logged_in_client.get(
            f"/leave/delete/{test_leave.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Conge supprime" in response.data or b"succes" in response.data

        # Vérifier que le congé a été supprimé
        from app.models import Leave

        leave = Leave.query.get(test_leave.id)
        assert leave is None

    def test_user_cannot_delete_others_leave(
        self, client, test_leave, second_user, app
    ):
        """Test qu'un utilisateur ne peut pas supprimer le congé d'un autre."""
        with app.app_context():
            # Connecter second_user
            client.post(
                "/login",
                data={"email": second_user.email, "password": "second123"},
                follow_redirects=True,
            )

            # Essayer de supprimer le congé de test_user (qui appartient à test_leave)
            response = client.get(
                f"/leave/delete/{test_leave.id}", follow_redirects=True
            )
            assert response.status_code == 200
            # Le message d'erreur devrait être présent
            assert b"Acces refuse" in response.data or b"vos propres" in response.data

            # Vérifier que le congé n'a pas été supprimé
            from app.models import Leave

            leave = Leave.query.get(test_leave.id)
            assert leave is not None

    def test_admin_can_delete_any_leave(self, logged_in_admin_client, test_leave, app):
        """Test qu'un admin peut supprimer n'importe quel congé."""
        response = logged_in_admin_client.get(
            f"/leave/delete/{test_leave.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Conge supprime" in response.data or b"succes" in response.data

        # Vérifier que le congé a été supprimé
        from app.models import Leave

        leave = Leave.query.get(test_leave.id)
        assert leave is None


class TestShiftPermissions:
    """Tests pour les permissions sur les shifts."""

    def test_admin_can_add_shift(
        self, logged_in_admin_client, test_user, test_shift_type
    ):
        """Test qu'un admin peut ajouter un shift."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2025-12-01",
            "end_date": "2025-12-01",
        }
        response = logged_in_admin_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shifts ajoute" in response.data or b"succes" in response.data

    def test_non_admin_cannot_add_shift(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Test qu'un utilisateur normal ne peut pas ajouter un shift."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2025-12-01",
            "end_date": "2025-12-01",
        }
        response = logged_in_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # L'utilisateur est redirigé avec un message d'erreur
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )

    def test_admin_can_delete_shift(self, logged_in_admin_client, test_shift):
        """Test qu'un admin peut supprimer un shift."""
        response = logged_in_admin_client.get(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shift supprime" in response.data or b"succes" in response.data

        from app.models import Shift

        shift = Shift.query.get(test_shift.id)
        assert shift is None

    def test_non_admin_cannot_delete_shift(self, logged_in_client, test_shift):
        """Test qu'un utilisateur normal ne peut pas supprimer un shift."""
        response = logged_in_client.get(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestOnCallPermissions:
    """Tests pour les permissions sur les astreintes."""

    def test_admin_can_add_oncall(self, logged_in_admin_client, test_user):
        """Test qu'un admin peut ajouter une astreinte."""
        # Trouver un vendredi dans le futur
        now = datetime.now()
        days_until_friday = (4 - now.weekday()) % 7
        friday_date = (now + timedelta(days=days_until_friday + 7)).strftime("%Y-%m-%d")

        data = {"user_id": test_user.id, "start_date": friday_date}
        response = logged_in_admin_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte ajoutee" in response.data or b"succes" in response.data

    def test_non_admin_cannot_add_oncall(self, logged_in_client, test_user):
        """Test qu'un utilisateur normal ne peut pas ajouter une astreinte."""
        data = {"user_id": test_user.id, "start_date": "2025-12-06"}  # Un vendredi
        response = logged_in_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )

    def test_admin_can_delete_oncall(self, logged_in_admin_client, test_oncall):
        """Test qu'un admin peut supprimer une astreinte."""
        response = logged_in_admin_client.get(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte supprimee" in response.data or b"succes" in response.data

        from app.models import OnCall

        oncall = OnCall.query.get(test_oncall.id)
        assert oncall is None

    def test_non_admin_cannot_delete_oncall(self, logged_in_client, test_oncall):
        """Test qu'un utilisateur normal ne peut pas supprimer une astreinte."""
        response = logged_in_client.get(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestLeavePermissions:
    """Tests pour les permissions sur les congés."""

    def test_user_can_add_own_leave(self, logged_in_client, test_user):
        """Test qu'un utilisateur peut ajouter son propre congé."""
        data = {
            "user_id": test_user.id,
            "start_date": "2025-12-20",
            "end_date": "2025-12-25",
        }
        response = logged_in_client.post("/leave/add", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Conge ajoute" in response.data or b"succes" in response.data

    def test_user_cannot_add_others_leave(self, client, test_user, second_user, app):
        """Test qu'un utilisateur ne peut pas ajouter un congé pour un autre."""
        with app.app_context():
            # Connecter second_user
            client.post(
                "/login",
                data={"email": second_user.email, "password": "second123"},
                follow_redirects=True,
            )

            # Essayer d'ajouter un congé pour test_user
            data = {
                "user_id": test_user.id,
                "start_date": "2025-12-20",
                "end_date": "2025-12-25",
            }
            response = client.post("/leave/add", data=data, follow_redirects=True)
            assert response.status_code == 200
            # Le message d'erreur devrait être présent
            # Le message est "Vous ne pouvez ajouter des congés que pour vous-même."
            # On vérifie en ASCII pour éviter les problèmes d'encodage
            assert (
                b"vous" in response.data.lower()
                and b"pour vous" in response.data.lower()
                or b"Seuls" in response.data
            )

    def test_admin_can_add_leave_for_anyone(self, logged_in_admin_client, test_user):
        """Test qu'un admin peut ajouter un congé pour n'importe qui."""
        data = {
            "user_id": test_user.id,
            "start_date": "2025-12-20",
            "end_date": "2025-12-25",
        }
        response = logged_in_admin_client.post(
            "/leave/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Conge ajoute" in response.data or b"succes" in response.data
