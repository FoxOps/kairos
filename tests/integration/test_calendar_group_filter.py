"""
Tests for the calendar (/) rehaul's group-awareness: the multi-group
filter's default selection (admin = every group, regular user = own
group, extensible - not a restriction), the group-color legend/dots,
and the removal of the old "Mode édition" toggle in favor of always-on
drag & drop + click-to-edit modals.
"""

from app import db
from app.models import Group


class TestCalendarGroupFilterDefaults:
    def test_admin_defaults_to_every_group_checked(
        self, test_app, logged_in_client, test_group
    ):
        other_group = Group(
            name="Other Group Calendar Default",
            is_part_of_schedule=True,
            is_part_of_oncall=False,
        )
        db.session.add(other_group)
        db.session.commit()

        resp = logged_in_client.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)

        assert f'value="{other_group.id}"' in body
        # Both groups' checkboxes appear checked for an admin.
        assert body.count("checked") >= 2

    def test_regular_user_defaults_to_own_group_only(
        self, test_app, non_admin_client, test_user, test_group
    ):
        other_group = Group(
            name="Other Group Non Admin Default",
            is_part_of_schedule=False,
            is_part_of_oncall=True,
        )
        db.session.add(other_group)
        db.session.commit()

        resp = non_admin_client.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)

        # The regular user's own group's checkbox is checked; the other
        # group's is present (extensible - not hidden/restricted) but
        # unchecked by default.
        own_group_pos = body.index(f'value="{test_group.id}"')
        own_group_checked = "checked" in body[own_group_pos : own_group_pos + 120]
        assert own_group_checked

        other_group_pos = body.index(f'value="{other_group.id}"')
        other_group_checked = "checked" in body[other_group_pos : other_group_pos + 120]
        assert not other_group_checked

    def test_excludes_group_in_neither_schedule_nor_oncall(
        self, test_app, logged_in_client, test_group, group_not_in_schedule
    ):
        """A group flagged for neither shift scheduling nor on-call
        rotation never has events to show here, so it's excluded from
        the filter/legend entirely - unlike test_group and other_group
        above, which are always eligible for at least one."""
        resp = logged_in_client.get("/")
        body = resp.get_data(as_text=True)
        assert f'value="{group_not_in_schedule.id}"' not in body

    def test_filter_not_restricted_to_admin(self, test_app, non_admin_client):
        """The group filter dropdown must be visible to every logged-in
        user, not just admins (confirmed via direct question: default
        selection differs by role, visibility doesn't)."""
        resp = non_admin_client.get("/")
        body = resp.get_data(as_text=True)
        assert "group-filter-checkbox" in body


class TestCalendarGroupColorData:
    def test_group_color_map_injected_for_js(self, test_app, logged_in_client):
        """Must be a <script type="application/json"> block (same pattern
        as #i18n-strings), not a data-* HTML attribute: tojson's raw
        double quotes terminate an attribute early and truncate the
        value, breaking JSON.parse client-side (real bug caught via a
        browser console SyntaxError)."""
        import re

        resp = logged_in_client.get("/")
        body = resp.get_data(as_text=True)
        assert "data-group-color-map=" not in body

        match = re.search(
            r'<script type="application/json" id="group-color-map-data">'
            r"(.*?)</script>",
            body,
            re.DOTALL,
        )
        assert match is not None
        import json

        json.loads(match.group(1))

    def test_current_user_id_injected_for_js(self, test_app, logged_in_client):
        from app.models import User

        resp = logged_in_client.get("/")
        body = resp.get_data(as_text=True)
        login_user = User.query.filter_by(email="login@example.com").first()
        assert f'data-current-user-id="{login_user.id}"' in body

    def test_legend_shows_group_names(self, test_app, logged_in_client, test_group):
        resp = logged_in_client.get("/")
        body = resp.get_data(as_text=True)
        assert test_group.name in body


class TestEditModeToggleRemoved:
    def test_no_edit_mode_toggle_button(self, test_app, logged_in_client):
        resp = logged_in_client.get("/")
        body = resp.get_data(as_text=True)
        assert "toggle-edit-mode" not in body
        assert "edit-mode-status-tag" not in body
