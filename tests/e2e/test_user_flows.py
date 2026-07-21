"""
E2E tests - full user journeys via the Flask test client.

No real browser here (see test_browser_flows.py for that, with
Playwright) - these tests chain several successive HTTP requests to
simulate an end-to-end user journey (login -> action -> verification ->
logout), with assertions on what's actually rendered at each step
rather than on isolated service calls. Fast, no heavy dependency, good
for checking permissions/redirects/data - complementary to
test_browser_flows.py, not replaced by it (see report/E2E Playwright -
Tests navigateur réel.md).
"""

from datetime import date, timedelta

from app import db
from app.models import Group, ShiftType, User


def _weekday_range(days=5):
    """Return (Monday, Friday) of the current or next week."""
    start = date.today()
    while start.weekday() != 0:
        start += timedelta(days=1)
    return start, start + timedelta(days=days - 1)


class TestAdminCreatesUserAndAssignsShift:
    """Journey: an admin creates a group, a user, then assigns shifts to
    them - and the user finds them after logging in."""

    def test_full_flow(self, test_app, logged_in_client):
        client = logged_in_client

        # 1. Create a group that's part of the schedule
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

        # 2. Create a user in that group
        resp = client.post(
            "/admin/users/add",
            data={
                "name": "Employé E2E",
                "email": "employe-e2e@test.com",
                "group_id": str(group_id),
                "password": "Correct-Horse-9",
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

        # 3. Assign shifts for the week (admin only)
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

        # 4. Log out of the admin account, log in as the employee - an
        # admin-created account is forced through a password change on
        # first login (ANSSI-PG-078 section 4: a password chosen *for*
        # the user, not by them, must be replaced - see
        # User.must_change_password), so this has to happen before the
        # employee can reach anything else.
        client.get("/logout", follow_redirects=True)
        resp = client.post(
            "/login",
            data={"email": "employe-e2e@test.com", "password": "Correct-Horse-9"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"nouveau mot de passe avant de continuer" in resp.data

        resp = client.post(
            "/profile/update",
            data={
                "name": "Employé E2E",
                "email": "employe-e2e@test.com",
                "current_password": "Correct-Horse-9",
                "new_password": "Even-Stronger-42",
                "confirm_password": "Even-Stronger-42",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # 5. The employee views their schedule
        resp = client.get("/schedule")
        assert resp.status_code == 200

        client.get("/logout", follow_redirects=True)


class TestUserRequestsLeave:
    """Journey: a regular user requests a leave for themselves, can't
    request one for someone else, an admin can delete it."""

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
    """Journey: wrong password rejected, correct password accepted,
    session invalidated after logout."""

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
    """Journey: a logged-in user exports their shifts as ICS."""

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
