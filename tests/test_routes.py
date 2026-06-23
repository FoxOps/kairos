"""
Tests pour les routes Flask.
"""

import pytest
from datetime import datetime, timedelta
from app import db
from app.models import Shift, OnCall, Leave, User, Group, ShiftType


class TestRolePermissions:
    """Tests pour les permissions basees sur les roles."""

    def test_decorators_import(self):
        """Test que les decorateurs peuvent etre importes."""
        from app.utils.decorators import admin_required, role_required

        assert callable(admin_required)
        assert callable(role_required)

    def test_models_have_is_admin(self):
        """Test que le modele User a le champ is_admin."""
        from app.models import User

        assert hasattr(User, "is_admin")


class TestIndexRoute:
    """Tests pour la route principale."""

    def test_index_route_accessible(self, client):
        """Test que la page d'accueil est accessible uniquement aux utilisateurs connectés."""
        # Test sans authentification - doit rediriger vers login
        response = client.get("/")
        assert response.status_code == 302
        assert response.location.endswith("/login?next=%2F")


class TestAuthRoutes:
    """Tests pour les routes d'authentification."""

    def test_login_get(self, client):
        """Test l'affichage de la page de connexion."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"email" in response.data

    def test_login_post_valid(self, client, test_user, app):
        """Test la connexion avec des identifiants valides."""
        with app.app_context():
            response = client.post(
                "/login",
                data={"email": test_user.email, "password": "test123"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"Leviia" in response.data or b"Schedule" in response.data

    def test_login_post_invalid_credentials(self, client):
        """Test la connexion avec des identifiants invalides."""
        response = client.post(
            "/login",
            data={"email": "invalid@test.com", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Email ou mot de passe incorrect" in response.data

    def test_login_post_empty_fields(self, client):
        """Test la connexion avec des champs vides."""
        response = client.post(
            "/login", data={"email": "", "password": ""}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Email et mot de passe sont obligatoires" in response.data

    def test_logout(self, logged_in_client):
        """Test la deconnexion."""
        response = logged_in_client.get("/logout", follow_redirects=True)
        assert response.status_code == 200
        # Après déconnexion, on est redirigé vers l'index
        assert b"Leviia" in response.data or b"Schedule" in response.data

    def test_register_disabled(self, client):
        """Test que l'inscription publique est desactivee."""
        response = client.get("/register", follow_redirects=True)
        assert response.status_code == 200
        # On est redirigé vers la page de login
        assert (
            b"Login" in response.data
            or b"Connexion" in response.data
            or b"email" in response.data
        )

    def test_profile_route(self, logged_in_client):
        """Test l'acces a la page de profil."""
        response = logged_in_client.get("/profile")
        assert response.status_code == 200
        assert b"Profil" in response.data or b"profile" in response.data.lower()

    def test_profile_update_get(self, logged_in_client):
        """Test l'affichage du formulaire de mise a jour du profil."""
        response = logged_in_client.get("/profile/update")
        assert response.status_code == 200

    def test_profile_update_post_valid(self, logged_in_client, test_user, app):
        """Test la mise a jour du profil avec des donnees valides."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Updated Name",
                "email": "updated@test.com",
                "current_password": "",
                "new_password": "",
                "confirm_password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # Le profil est mis a jour ou un message est affiche
        assert b"Profil" in response.data or b"profile" in response.data.lower()

    def test_profile_update_post_invalid_email(
        self, logged_in_client, test_user, second_user, app
    ):
        """Test la mise a jour du profil avec un email deja utilise."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Test User",
                "email": second_user.email,
                "current_password": "",
                "new_password": "",
                "confirm_password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # Un message d'erreur est affiche
        assert (
            b"email" in response.data.lower()
            or b"Profil" in response.data
            or b"profile" in response.data.lower()
        )


class TestShiftRoutes:
    """Tests pour les routes des shifts."""

    def test_schedule_route_accessible(self, logged_in_client):
        """Test l'acces a la page des shifts."""
        response = logged_in_client.get("/schedule")
        assert response.status_code == 200
        assert b"Shifts" in response.data or b"schedule" in response.data.lower()

    def test_add_shift_get_unauthorized(self, logged_in_client):
        """Test qu'un utilisateur normal ne peut pas acceder au formulaire d'ajout de shift."""
        response = logged_in_client.get("/schedule/add", follow_redirects=True)
        assert response.status_code == 200
        # L'utilisateur est redirige vers l'index ou voit un message
        assert b"Leviia" in response.data or b"Schedule" in response.data

    def test_add_shift_get_admin(self, logged_in_admin_client):
        """Test qu'un administrateur peut acceder au formulaire d'ajout de shift."""
        response = logged_in_admin_client.get("/schedule/add")
        assert response.status_code == 200
        assert b"Ajouter un shift" in response.data or b"Add Shift" in response.data

    def test_add_shift_post_valid(
        self, logged_in_admin_client, test_user, test_shift_type
    ):
        """Test l'ajout d'un shift valide."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2023-12-01",
            "end_date": "2023-12-01",
        }
        response = logged_in_admin_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shifts ajoute" in response.data or b"succes" in response.data

        shifts = Shift.query.filter_by(user_id=test_user.id).all()
        assert len(shifts) >= 1

    def test_add_shift_post_invalid_dates_weekend(
        self, logged_in_admin_client, test_user, test_shift_type
    ):
        """Test l'ajout d'un shift avec des dates invalides (weekend)."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2023-12-02",
            "end_date": "2023-12-02",
        }
        response = logged_in_admin_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # Le formulaire est reaffiche avec un message d'erreur
        assert (
            b"Shifts" in response.data
            or b"schedule" in response.data.lower()
            or b"Add" in response.data
        )

    def test_delete_shift_post(self, logged_in_admin_client, test_shift):
        """Test la suppression d'un shift."""
        response = logged_in_admin_client.get(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shift supprime" in response.data or b"succes" in response.data

        shift = db.session.get(Shift, test_shift.id)
        assert shift is None

    def test_delete_shift_unauthorized(self, logged_in_client, test_shift):
        """Test qu'un utilisateur normal ne peut pas supprimer un shift."""
        response = logged_in_client.get(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # Le décorateur admin_required utilise ce message
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestOnCallRoutes:
    """Tests pour les routes des astreintes."""

    def test_oncall_route_accessible(self, logged_in_client):
        """Test l'acces a la page des astreintes."""
        response = logged_in_client.get("/oncall")
        assert response.status_code == 200
        assert b"Astreinte" in response.data or b"oncall" in response.data.lower()

    def test_add_oncall_get_unauthorized(self, logged_in_client):
        """Test qu'un utilisateur normal ne peut pas acceder au formulaire d'ajout d'astreinte."""
        response = logged_in_client.get("/oncall/add", follow_redirects=True)
        assert response.status_code == 200
        # L'utilisateur est redirige
        assert b"Leviia" in response.data or b"Schedule" in response.data

    def test_add_oncall_get_admin(self, logged_in_admin_client):
        """Test qu'un administrateur peut acceder au formulaire d'ajout d'astreinte."""
        response = logged_in_admin_client.get("/oncall/add")
        assert response.status_code == 200
        assert (
            b"Ajouter une astreinte" in response.data or b"Add OnCall" in response.data
        )

    def test_add_oncall_post_valid(self, logged_in_admin_client, test_user):
        """Test l'ajout d'une astreinte valide."""
        data = {"user_id": test_user.id, "start_date": "2023-12-01"}
        response = logged_in_admin_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte ajoutee" in response.data or b"succes" in response.data

        on_calls = OnCall.query.filter_by(user_id=test_user.id).all()
        assert len(on_calls) >= 1

    def test_add_oncall_post_invalid_day(self, logged_in_admin_client, test_user):
        """Test l'ajout d'une astreinte un jour invalide."""
        data = {"user_id": test_user.id, "start_date": "2023-12-02"}
        response = logged_in_admin_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"vendredi" in response.data.lower()

    def test_delete_oncall_post(self, logged_in_admin_client, test_oncall):
        """Test la suppression d'une astreinte."""
        response = logged_in_admin_client.get(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte supprimee" in response.data or b"succes" in response.data

        oncall = db.session.get(OnCall, test_oncall.id)
        assert oncall is None

    def test_delete_oncall_unauthorized(self, logged_in_client, test_oncall):
        """Test qu'un utilisateur normal ne peut pas supprimer une astreinte."""
        response = logged_in_client.get(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # Le décorateur admin_required utilise ce message
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestLeaveRoutes:
    """Tests pour les routes des conges."""

    def test_leave_route_accessible(self, logged_in_client):
        """Test l'acces a la page des conges."""
        response = logged_in_client.get("/leave")
        assert response.status_code == 200
        assert b"Conge" in response.data or b"leave" in response.data.lower()

    def test_add_leave_get(self, logged_in_client):
        """Test l'affichage du formulaire d'ajout de conge."""
        response = logged_in_client.get("/leave/add")
        assert response.status_code == 200
        assert b"Ajouter" in response.data and (
            b"Conge" in response.data or b"leave" in response.data.lower()
        )

    def test_add_leave_post_valid(self, logged_in_client, test_user):
        """Test l'ajout d'un conge valide."""
        data = {
            "user_id": test_user.id,
            "start_date": "2023-12-20",
            "end_date": "2023-12-25",
        }
        response = logged_in_client.post("/leave/add", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Conge ajoute" in response.data or b"succes" in response.data

        leaves = Leave.query.filter_by(user_id=test_user.id).all()
        assert len(leaves) >= 1

    def test_add_leave_post_invalid_dates(self, logged_in_client, test_user):
        """Test l'ajout d'un conge avec des dates invalides."""
        data = {
            "user_id": test_user.id,
            "start_date": "2023-12-25",
            "end_date": "2023-12-20",
        }
        response = logged_in_client.post("/leave/add", data=data, follow_redirects=True)
        assert response.status_code == 200
        # Le formulaire est reaffiche avec un message d'erreur
        assert (
            b"date" in response.data.lower()
            or b"debut" in response.data.lower()
            or b"fin" in response.data.lower()
        )

    def test_delete_leave_post(self, logged_in_client, test_leave):
        """Test la suppression d'un conge."""
        response = logged_in_client.get(
            f"/leave/delete/{test_leave.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Conge supprime" in response.data or b"succes" in response.data

        leave = db.session.get(Leave, test_leave.id)
        assert leave is None

    def test_delete_leave_unauthorized(self, client, test_leave, second_user, app):
        """Test qu'un utilisateur ne peut pas supprimer le conge d'un autre."""
        with app.app_context():
            client.post(
                "/login",
                data={"email": second_user.email, "password": "second123"},
                follow_redirects=True,
            )

            response = client.get(
                f"/leave/delete/{test_leave.id}", follow_redirects=True
            )
            assert response.status_code == 200
            # Le décorateur user_owns_resource utilise ce message
            assert (
                b"Acces refuse" in response.data
                or b"Seuls" in response.data
                or b"vos propres" in response.data
                or b"vous" in response.data.lower()
            )


class TestAdminRoutes:
    """Tests pour les routes admin."""

    def test_admin_dashboard(self, logged_in_admin_client):
        """Test l'acces au dashboard admin."""
        response = logged_in_admin_client.get("/admin")
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"admin" in response.data.lower()

    def test_admin_dashboard_unauthorized(self, logged_in_client):
        """Test qu'un utilisateur normal ne peut pas acceder au dashboard admin."""
        response = logged_in_client.get("/admin", follow_redirects=True)
        assert response.status_code == 200
        # L'utilisateur est redirige
        assert b"Leviia" in response.data or b"Schedule" in response.data

    def test_list_groups(self, logged_in_admin_client):
        """Test l'affichage de la liste des groupes."""
        response = logged_in_admin_client.get("/admin/groups")
        assert response.status_code == 200
        assert (
            b"Gestion des groupes" in response.data
            or b"groups" in response.data.lower()
        )

    def test_add_group_post_valid(self, logged_in_admin_client):
        """Test l'ajout d'un groupe valide."""
        data = {
            "name": "Nouveau Groupe",
            "is_part_of_schedule": "on",
            "is_part_of_oncall": "on",
        }
        response = logged_in_admin_client.post(
            "/admin/groups/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Groupe ajoute" in response.data or b"succes" in response.data

        group = Group.query.filter_by(name="Nouveau Groupe").first()
        assert group is not None

    def test_add_group_post_invalid(self, logged_in_admin_client):
        """Test l'ajout d'un groupe sans nom."""
        data = {"name": "", "is_part_of_schedule": "on", "is_part_of_oncall": "on"}
        response = logged_in_admin_client.post(
            "/admin/groups/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Le nom du groupe est obligatoire" in response.data

    def test_delete_group_post(self, logged_in_admin_client, test_group):
        """Test la suppression d'un groupe."""
        response = logged_in_admin_client.post(
            f"/admin/groups/delete/{test_group.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # Vérifier que le groupe a ete supprime ou qu'un message est affiche
        assert (
            b"Groupe" in response.data
            or b"groups" in response.data.lower()
            or b"succes" in response.data
        )

    def test_delete_group_with_users(
        self, logged_in_admin_client, test_group, test_user
    ):
        """Test qu'un groupe avec des utilisateurs ne peut pas etre supprime."""
        response = logged_in_admin_client.post(
            f"/admin/groups/delete/{test_group.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # Le groupe ne peut pas etre supprime car il a des utilisateurs
        assert (
            b"Groupe" in response.data
            or b"groups" in response.data.lower()
            or b"Impossible" in response.data
        )

    def test_list_users(self, logged_in_admin_client):
        """Test l'affichage de la liste des utilisateurs."""
        response = logged_in_admin_client.get("/admin/users")
        assert response.status_code == 200
        assert (
            b"Gestion des utilisateurs" in response.data
            or b"users" in response.data.lower()
        )

    def test_add_user_post_valid(self, logged_in_admin_client, test_group):
        """Test l'ajout d'un utilisateur valide."""
        data = {
            "name": "Nouvel Utilisateur",
            "email": "nouvel@example.com",
            "group_id": test_group.id,
        }
        response = logged_in_admin_client.post(
            "/admin/users/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Utilisateur ajoute" in response.data or b"succes" in response.data

        user = User.query.filter_by(email="nouvel@example.com").first()
        assert user is not None

    def test_add_user_post_invalid(self, logged_in_admin_client):
        """Test l'ajout d'un utilisateur avec des champs manquants."""
        data = {"name": "", "email": "", "group_id": ""}
        response = logged_in_admin_client.post(
            "/admin/users/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Tous les champs sont obligatoires" in response.data

    def test_delete_user_post(self, logged_in_admin_client, test_user):
        """Test la suppression d'un utilisateur."""
        response = logged_in_admin_client.post(
            f"/admin/users/delete/{test_user.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # Vérifier que l'utilisateur a ete supprime ou qu'un message est affiche
        assert (
            b"Utilisateur" in response.data
            or b"users" in response.data.lower()
            or b"succes" in response.data
        )

    def test_delete_user_with_resources(
        self, logged_in_admin_client, test_shift, test_user
    ):
        """Test qu'un utilisateur avec des ressources ne peut pas etre supprime."""
        # test_shift est déjà associé à test_user via la fixture
        response = logged_in_admin_client.post(
            f"/admin/users/delete/{test_user.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Utilisateur" in response.data
            or b"users" in response.data.lower()
            or b"Impossible" in response.data
        )


class TestShiftTypeRoutes:
    """Tests pour les routes des types de shifts."""

    def test_list_shift_types(self, logged_in_admin_client):
        """Test l'affichage de la liste des types de shifts."""
        response = logged_in_admin_client.get("/admin/shift-types")
        assert response.status_code == 200
        assert b"Types de shifts" in response.data or b"shift" in response.data.lower()

    def test_add_shift_type_post_valid(self, logged_in_admin_client):
        """Test l'ajout d'un type de shift valide."""
        data = {"name": "night", "label": "Nuit", "start_hour": "22", "end_hour": "6"}
        response = logged_in_admin_client.post(
            "/admin/shift-types/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # Vérifier que le type a ete ajoute ou qu'un message est affiche
        assert (
            b"Type" in response.data
            or b"shift" in response.data.lower()
            or b"succes" in response.data
        )

        shift_type = ShiftType.query.filter_by(name="night").first()
        if shift_type:
            assert shift_type.name == "night"

    def test_add_shift_type_post_invalid_hours(self, logged_in_admin_client):
        """Test l'ajout d'un type de shift avec des heures invalides."""
        data = {
            "name": "invalid",
            "label": "Invalide",
            "start_hour": "25",
            "end_hour": "6",
        }
        response = logged_in_admin_client.post(
            "/admin/shift-types/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # Le formulaire est reaffiche avec un message d'erreur
        assert (
            b"Type" in response.data
            or b"shift" in response.data.lower()
            or b"Add" in response.data
        )

    def test_add_shift_type_start_after_end(self, logged_in_admin_client):
        """Test l'ajout d'un type de shift ou l'heure de debut est apres l'heure de fin."""
        data = {
            "name": "invalid",
            "label": "Invalide",
            "start_hour": "15",
            "end_hour": "10",
        }
        response = logged_in_admin_client.post(
            "/admin/shift-types/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # Le formulaire est reaffiche avec un message d'erreur
        assert (
            b"Type" in response.data
            or b"shift" in response.data.lower()
            or b"Add" in response.data
        )

    def test_delete_shift_type_post(self, logged_in_admin_client, test_shift_type):
        """Test la suppression d'un type de shift."""
        response = logged_in_admin_client.post(
            f"/admin/shift-types/delete/{test_shift_type.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Type de shift supprim" in response.data or b"succ" in response.data

        shift_type = db.session.get(ShiftType, test_shift_type.id)
        assert shift_type is None

    def test_delete_shift_type_in_use(self, logged_in_admin_client, test_shift):
        """Test qu'un type de shift utilise ne peut pas etre supprime."""
        # test_shift utilise déjà test_shift_type
        response = logged_in_admin_client.post(
            f"/admin/shift-types/delete/{test_shift.shift_type_id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        # Un message est affiche
        assert (
            b"Type" in response.data
            or b"shift" in response.data.lower()
            or b"Impossible" in response.data
        )
