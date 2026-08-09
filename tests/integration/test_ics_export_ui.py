"""
Tests for the ICS export UI: the unified single-button/modal
(app/templates/_ics_export_buttons.html) replacing the old paired
all/my buttons, and its group-scoping (checkbox list + Moi/Tout le
monde toggle).
"""

from app import db
from app.models import Group, User


def _give_logged_in_client_a_token(client):
    """No `with app_context()` wrapper here on purpose: test_app's own
    fixture already keeps one app context (and its db.session) open for
    the whole test. Flask-Login's user_loader resolves current_user via
    db.session.get() (an identity-map shortcut) - mutating the User
    through a *different*, nested app_context() would commit fine but
    leave that outer session's cached object stale, so the very next
    request would still see the old (token-less) user."""
    user = User.query.filter_by(email="login@example.com").first()
    user.generate_ics_token()
    db.session.commit()
    return user.group_id


class TestUnifiedExportButton:
    def test_schedule_has_one_export_button_per_resource(
        self, test_app, logged_in_client
    ):
        _give_logged_in_client_a_token(logged_in_client)
        resp = logged_in_client.get("/schedule")
        body = resp.get_data(as_text=True)

        assert 'id="ics-modal-shifts"' in body
        # Old paired all/my ids must be gone.
        assert "ics-modal-shifts-all" not in body
        assert "ics-modal-shifts-my" not in body

    def test_schedule_export_modal_has_group_checkboxes(
        self, test_app, logged_in_client
    ):
        own_group_id = _give_logged_in_client_a_token(logged_in_client)
        resp = logged_in_client.get("/schedule")
        body = resp.get_data(as_text=True)

        assert "ics-export-group-checkbox" in body
        assert f'value="{own_group_id}"' in body

    def test_schedule_export_modal_defaults_to_own_group_only(
        self, test_app, logged_in_client
    ):
        own_group_id = _give_logged_in_client_a_token(logged_in_client)
        other_group = Group(
            name="Other Group Export UI",
            is_part_of_schedule=True,
            is_part_of_oncall=True,
        )
        db.session.add(other_group)
        db.session.commit()
        other_group_id = other_group.id

        resp = logged_in_client.get("/schedule")
        body = resp.get_data(as_text=True)

        own_pos = body.index(f'value="{own_group_id}"')
        assert "checked" in body[own_pos : own_pos + 200]

        other_pos = body.index(f'value="{other_group_id}"')
        assert "checked" not in body[other_pos : other_pos + 200]

    def test_schedule_export_modal_default_scope_is_my(
        self, test_app, logged_in_client
    ):
        """Own group is checked by default, so the toggle defaults to
        "Moi" (unchecked) and the initial copyable URL uses scope=my."""
        _give_logged_in_client_a_token(logged_in_client)
        resp = logged_in_client.get("/schedule")
        body = resp.get_data(as_text=True)

        assert "scope=my" in body
        toggle_pos = body.index("ics-export-scope-toggle")
        toggle_tag = body[toggle_pos - 200 : toggle_pos + 50]
        assert "checked" not in toggle_tag
        assert "disabled" not in toggle_tag

    def test_export_url_input_has_an_aria_label(self, test_app, logged_in_client):
        """The copyable URL <input> has no visible <label> (the
        "Copier" button next to it is the only visible affordance) -
        without an aria-label, a screen reader announces it as an
        unlabelled text field."""
        _give_logged_in_client_a_token(logged_in_client)
        resp = logged_in_client.get("/schedule")
        body = resp.get_data(as_text=True)

        input_pos = body.index('id="ics-modal-shifts-input"')
        input_tag = body[input_pos - 50 : input_pos + 300]
        assert "aria-label=" in input_tag

    def test_oncall_and_leave_also_have_single_export_button(
        self, test_app, logged_in_client
    ):
        _give_logged_in_client_a_token(logged_in_client)

        oncall_body = logged_in_client.get("/oncall").get_data(as_text=True)
        assert 'id="ics-modal-oncall"' in oncall_body

        leave_body = logged_in_client.get("/leave").get_data(as_text=True)
        assert 'id="ics-modal-leaves"' in leave_body

    def test_admin_dashboard_defaults_to_all_groups_no_toggle(
        self, test_app, logged_in_client
    ):
        """admin/dashboard.html passes show_my=false (no personal-scope
        toggle) and the route passes default_all_groups=True (every
        eligible group checked, not just the admin's own)."""
        own_group_id = _give_logged_in_client_a_token(logged_in_client)
        other_group = Group(
            name="Other Group Admin Dashboard",
            is_part_of_schedule=True,
            is_part_of_oncall=True,
        )
        db.session.add(other_group)
        db.session.commit()
        other_group_id = other_group.id

        resp = logged_in_client.get("/admin")
        body = resp.get_data(as_text=True)

        assert "ics-export-scope-toggle" not in body
        assert "scope=all" in body

        own_pos = body.index(f'value="{own_group_id}"')
        assert "checked" in body[own_pos : own_pos + 200]
        other_pos = body.index(f'value="{other_group_id}"')
        assert "checked" in body[other_pos : other_pos + 200]


class TestIcsTokenPageReusesExportModal:
    """/profile/ics-token used to list 6 static readonly URL rows
    (shifts/oncall/leaves x all/my) - it now reuses the same
    _ics_export_buttons.html partial as /schedule, /oncall, /leave."""

    def test_shows_one_export_modal_per_resource(self, test_app, logged_in_client):
        _give_logged_in_client_a_token(logged_in_client)
        resp = logged_in_client.get("/profile/ics-token")
        body = resp.get_data(as_text=True)

        assert 'id="ics-modal-shifts"' in body
        assert 'id="ics-modal-oncall"' in body
        assert 'id="ics-modal-leaves"' in body
        # The old 6 static URL inputs are gone.
        assert "urlShiftsAllInput" not in body
        assert "urlShiftsMyInput" not in body
        assert "urlOncallAllInput" not in body
        assert "urlOncallMyInput" not in body
        assert "urlLeavesAllInput" not in body
        assert "urlLeavesMyInput" not in body

    def test_raw_token_input_still_present(self, test_app, logged_in_client):
        """Unrelated to this feature - the raw-token display/copy
        section must survive the rewrite untouched."""
        _give_logged_in_client_a_token(logged_in_client)
        resp = logged_in_client.get("/profile/ics-token")
        body = resp.get_data(as_text=True)

        assert 'id="tokenInput"' in body
        assert "Kairos.copyToken(event)" in body
