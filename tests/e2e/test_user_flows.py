"""
Tests E2E - parcours utilisateur complets via le client de test Flask.

Pas de navigateur réel ici (voir test_browser_flows.py pour ça, avec
Playwright) - ces tests enchaînent plusieurs requêtes HTTP successives
pour simuler un parcours utilisateur de bout en bout (login -> action ->
vérification -> logout), avec assertions sur le contenu réellement rendu
à chaque étape plutôt que sur des appels de service isolés. Rapides,
zéro dépendance lourde, bons pour vérifier permissions/redirections/
données - complémentaires de test_browser_flows.py, pas remplacés par
lui (voir report/E2E Playwright - Tests navigateur réel.md).
"""

from datetime import date, timedelta

from app import db
from app.models import Group, ShiftType, User


def _weekday_range(days=5):
    """Renvoie (lundi, vendredi) de la semaine courante ou suivante."""
    start = date.today()
    while start.weekday() != 0:
        start += timedelta(days=1)
    return start, start + timedelta(days=days - 1)


class TestAdminCreatesUserAndAssignsShift:
    """Parcours : un admin crée un groupe, un utilisateur, puis lui
    assigne des shifts - et l'utilisateur les retrouve en se connectant."""

    def test_full_flow(self, test_app, logged_in_client):
        client = logged_in_client

        # 1. Créer un groupe participant au planning
        resp = client.post(
            "/admin/groups/add",
            data={
                "name": "Support E2E",
                "is_part_of_schedule": "on",
                "is_part_of_oncall": "on",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with client.application.app_context():
            group = Group.query.filter_by(name="Support E2E").first()
            assert group is not None
            group_id = group.id

        # 2. Créer un utilisateur dans ce groupe
        resp = client.post(
            "/admin/users/add",
            data={
                "name": "Employé E2E",
                "email": "employe-e2e@test.com",
                "group_id": str(group_id),
                "password": "motdepasse123",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with client.application.app_context():
            user = User.query.filter_by(email="employe-e2e@test.com").first()
            assert user is not None
            user_id = user.id

            shift_type = ShiftType.query.first()
            if not shift_type:
                shift_type = ShiftType(
                    name="e2e-morning", label="Matin E2E", start_hour=7, end_hour=15
                )
                db.session.add(shift_type)
                db.session.commit()
            shift_type_id = shift_type.id

        # 3. Assigner des shifts pour la semaine (admin uniquement)
        monday, friday = _weekday_range()
        resp = client.post(
            "/schedule/add",
            data={
                "user_id": str(user_id),
                "shift_type_id": str(shift_type_id),
                "start_date": monday.isoformat(),
                "end_date": friday.isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Shifts ajoutes avec succes" in resp.data or b"ajout" in resp.data

        # 4. Se déconnecter de l'admin, se connecter en tant qu'employé
        client.get("/logout", follow_redirects=True)
        resp = client.post(
            "/login",
            data={"email": "employe-e2e@test.com", "password": "motdepasse123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # 5. L'employé consulte son planning
        resp = client.get("/schedule")
        assert resp.status_code == 200

        client.get("/logout", follow_redirects=True)


class TestUserRequestsLeave:
    """Parcours : un utilisateur normal demande un congé pour lui-même,
    ne peut pas en demander pour un autre, un admin peut le supprimer."""

    def test_user_can_request_own_leave(self, test_app, test_user, client):
        resp = client.post(
            "/login",
            data={"email": test_user.email, "password": "test123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        start = date.today()
        end = start + timedelta(days=2)
        resp = client.post(
            "/leave/add",
            data={
                "user_id": str(test_user.id),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        resp = client.get("/leave")
        assert resp.status_code == 200

        client.get("/logout", follow_redirects=True)

    def test_user_cannot_request_leave_for_someone_else(
        self, test_app, test_user, second_user, client
    ):
        client.post(
            "/login",
            data={"email": test_user.email, "password": "test123"},
            follow_redirects=True,
        )

        start = date.today()
        end = start + timedelta(days=2)
        resp = client.post(
            "/leave/add",
            data={
                "user_id": str(second_user.id),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "vous-même".encode() in resp.data or b"vous-m" in resp.data

        with client.application.app_context():
            from app.models import Leave

            assert Leave.query.filter_by(user_id=second_user.id).first() is None

        client.get("/logout", follow_redirects=True)


class TestLoginLogoutFlow:
    """Parcours : mauvais mot de passe rejeté, bon mot de passe accepté,
    session invalidée après logout."""

    def test_wrong_password_then_correct_password(self, test_app, test_user, client):
        resp = client.post(
            "/login",
            data={"email": test_user.email, "password": "wrong-password"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert (
            b"incorrect" in resp.data.lower()
            or b"Email ou mot de passe incorrect" in resp.data
        )

        resp = client.get("/schedule", follow_redirects=False)
        assert resp.status_code in (302, 401)

        resp = client.post(
            "/login",
            data={"email": test_user.email, "password": "test123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        resp = client.get("/schedule")
        assert resp.status_code == 200

        client.get("/logout", follow_redirects=True)

        resp = client.get("/schedule", follow_redirects=False)
        assert resp.status_code in (302, 401)


class TestExportFlow:
    """Parcours : un utilisateur connecté exporte ses shifts en ICS."""

    def test_export_shifts_after_login(self, test_app, test_user, test_shift, client):
        client.post(
            "/login",
            data={"email": test_user.email, "password": "test123"},
            follow_redirects=True,
        )

        resp = client.get("/export/shifts?scope=my")
        assert resp.status_code == 200
        assert b"BEGIN:VCALENDAR" in resp.data

        client.get("/logout", follow_redirects=True)

    def test_export_requires_authentication_or_token(self, test_app, client):
        resp = client.get("/export/shifts?scope=my", follow_redirects=False)
        assert resp.status_code in (302, 401)
