"""
Integration tests for /dashboard - day-based stat numbers and trend text
actually render, on top of the existing auth/CSP/perf coverage of this
route (test_security.py, test_performance.py, test_password_policy.py),
which stay untouched by this feature.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Leave, OnCall, Shift, ShiftType, User


def _login_user(client):
    with client.application.app_context():
        return User.query.filter_by(email="login@example.com").first()


class TestDashboardRouteRequiresAuth:
    def test_dashboard_redirects_when_not_logged_in(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/login" in response.location


class TestDashboardStatValues:
    def test_zero_data_renders_zero_stats(self, test_app, logged_in_client):
        response = logged_in_client.get("/dashboard")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Jours de shift" in html
        assert "Jours d'astreinte" in html
        assert "Jours de congé" in html
        assert "stable vs mois dernier" in html

    def test_shift_days_and_trend_render(self, test_app, logged_in_client):
        with logged_in_client.application.app_context():
            user = _login_user(logged_in_client)
            shift_type = ShiftType(
                name="dash-test", label="Dash Test", start_hour=7, end_hour=15
            )
            db.session.add(shift_type)
            db.session.flush()

            today = date.today()
            for offset in (0, 1):
                d = today.replace(day=1) + timedelta(days=offset)
                db.session.add(
                    Shift(
                        user_id=user.id,
                        shift_type_id=shift_type.id,
                        date=d,
                        start_time=datetime.combine(d, datetime.min.time()),
                        end_time=datetime.combine(d, datetime.min.time())
                        + timedelta(hours=8),
                    )
                )
            db.session.commit()

        response = logged_in_client.get("/dashboard")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert ">2<" in html  # total shift days
        assert "2 ce mois-ci" in html
        assert "+2 vs mois dernier" in html

    def test_leave_upcoming_card_uses_duration_method(self, test_app, logged_in_client):
        with logged_in_client.application.app_context():
            user = _login_user(logged_in_client)
            start = date.today() + timedelta(days=5)
            end = start + timedelta(days=2)  # 3 inclusive days
            db.session.add(Leave(user_id=user.id, start_date=start, end_date=end))
            db.session.commit()

        response = logged_in_client.get("/dashboard")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "3 jour(s)" in html

    def test_oncall_days_shown_as_whole_days_not_row_count(
        self, test_app, logged_in_client
    ):
        with logged_in_client.application.app_context():
            user = _login_user(logged_in_client)
            start = datetime.combine(date.today(), datetime.min.time())
            end = start + timedelta(hours=48)
            db.session.add(OnCall(user_id=user.id, start_time=start, end_time=end))
            db.session.commit()

        response = logged_in_client.get("/dashboard")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        # One OnCall row spanning 2 days must read as "2", not "1" (row count).
        assert ">2<" in html
