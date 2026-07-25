"""
Tests for the admin automation rules routes
(app/routes/admin_automation_rules_routes.py).
"""


class TestAutomationRulesDashboardGet:
    def test_dashboard_get(self, logged_in_client):
        response = logged_in_client.get("/admin/automation/rules")
        assert response.status_code == 200

    def test_dashboard_unauthenticated(self, client):
        response = client.get("/admin/automation/rules", follow_redirects=True)
        assert b"Connexion" in response.data


class TestWeekendDefinitionSection:
    def test_valid_days_persist(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "weekend_definition", "weekend_days": ["5", "6"]},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("weekend_definition") == {
            "weekend_days": [5, 6]
        }

    def test_no_days_selected_flashes_error(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "weekend_definition"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Erreur" in response.data


class TestOnCallSpacingSection:
    def test_valid_weeks_persist(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "oncall_spacing", "min_spacing_weeks": "3"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("oncall_spacing") == {
            "min_spacing_weeks": 3
        }


class TestOnCallShiftOverlapSection:
    def test_checkbox_checked_saves_true(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "oncall_shift_overlap", "block": "on"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("oncall_shift_overlap") == {"block": True}

    def test_checkbox_unchecked_saves_false(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "oncall_shift_overlap"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("oncall_shift_overlap") == {"block": False}


class TestStaffingLimitsSection:
    def test_valid_limits_persist(self, logged_in_client, test_shift_type):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "staffing_limits",
                f"min_{test_shift_type.id}": "1",
                f"max_{test_shift_type.id}": "3",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("staffing_limits") == {
            str(test_shift_type.id): {"min": 1, "max": 3}
        }

    def test_blank_fields_mean_no_limit(self, logged_in_client, test_shift_type):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "staffing_limits",
                f"min_{test_shift_type.id}": "",
                f"max_{test_shift_type.id}": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.utils.automation.rules import StaffingLimitsRule

        # Blank fields are omitted from storage entirely (the route
        # doesn't write a no-op entry) - get_limits() still correctly
        # reports "no limit either way" via its own missing-key default.
        assert StaffingLimitsRule.get_limits(test_shift_type.id) == {
            "min": None,
            "max": None,
        }


class TestMandatoryShiftSection:
    def test_selected_ids_persist(self, logged_in_client, test_shift_type):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "mandatory_shift",
                "mandatory_shift_type_ids": [str(test_shift_type.id)],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("mandatory_shift") == {
            "shift_type_ids": [test_shift_type.id]
        }

    def test_none_selected_persists_empty(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "mandatory_shift"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("mandatory_shift") == {
            "shift_type_ids": []
        }


class TestRestAfterOnCallSection:
    def test_valid_hours_persist(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "rest_after_oncall", "min_rest_hours": "8"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("rest_after_oncall") == {
            "min_rest_hours": 8
        }


class TestOnCallAnchorSection:
    def test_valid_anchor_persists(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "oncall_anchor",
                "weekday": "4",
                "start_hour": "21",
                "end_hour": "7",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("oncall_anchor") == {
            "weekday": 4,
            "start_hour": 21,
            "end_hour": 7,
        }


class TestSchedulingModeSection:
    def test_shift_mode_persists_independently_of_oncall(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "shift_scheduling_mode",
                "shift_scheduling_mode": "per_group",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_shift_scheduling_mode() == "per_group"
        assert SettingsService.get_oncall_scheduling_mode() == "shared"

    def test_oncall_mode_persists_independently_of_shift(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "oncall_scheduling_mode",
                "oncall_scheduling_mode": "per_group",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_oncall_scheduling_mode() == "per_group"
        assert SettingsService.get_shift_scheduling_mode() == "shared"

    def test_invalid_shift_mode_flashes_error_without_persisting(
        self, logged_in_client
    ):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "shift_scheduling_mode", "shift_scheduling_mode": "bogus"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Erreur" in response.data

        from app.services import SettingsService

        assert SettingsService.get_shift_scheduling_mode() == "shared"


class TestGroupScopedRuleEditing:
    def test_dashboard_get_with_group_id_shows_group_scoped_value(
        self, logged_in_client, test_group
    ):
        from app.models import AutomationRule

        AutomationRule.set("oncall_spacing", {"min_spacing_weeks": 4}, group=test_group)

        response = logged_in_client.get(
            f"/admin/automation/rules?group_id={test_group.id}"
        )
        assert response.status_code == 200
        assert b'name="min_spacing_weeks" min="1" value="4"' in response.data

    def test_post_with_group_id_saves_group_override_not_org_default(
        self, logged_in_client, test_group
    ):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "oncall_spacing",
                "min_spacing_weeks": "5",
                "group_id": str(test_group.id),
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("oncall_spacing", group=test_group) == {
            "min_spacing_weeks": 5
        }
        assert AutomationRule.resolve_params("oncall_spacing") is None

    def test_post_without_group_id_still_saves_org_default(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={"section": "oncall_spacing", "min_spacing_weeks": "5"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("oncall_spacing") == {
            "min_spacing_weeks": 5
        }


class TestOverrideBadges:
    def test_shows_personalized_badge_for_an_overridden_rule(
        self, logged_in_client, test_group
    ):
        from app.models import AutomationRule

        AutomationRule.set("oncall_spacing", {"min_spacing_weeks": 4}, group=test_group)

        response = logged_in_client.get(
            f"/admin/automation/rules?group_id={test_group.id}"
        )
        assert response.status_code == 200
        assert "Personnalisé" in response.data.decode()

    def test_shows_inherited_badge_for_a_non_overridden_rule(
        self, logged_in_client, test_group
    ):
        response = logged_in_client.get(
            f"/admin/automation/rules?group_id={test_group.id}"
        )
        assert response.status_code == 200
        assert "Hérité de l'organisation" in response.data.decode()

    def test_no_badges_shown_on_the_org_wide_view(self, logged_in_client):
        response = logged_in_client.get("/admin/automation/rules")
        assert response.status_code == 200
        body = response.data.decode()
        assert "Personnalisé" not in body
        assert "Hérité de l'organisation" not in body


class TestShiftSlotsSection:
    def test_valid_ids_persist(self, logged_in_client, test_shift_type):
        response = logged_in_client.post(
            "/admin/automation/rules",
            data={
                "section": "shift_slots",
                "oncall_shift_type_id": str(test_shift_type.id),
                "rotation_shift_type_id": str(test_shift_type.id),
                "default_shift_type_id": str(test_shift_type.id),
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.models import AutomationRule

        assert AutomationRule.resolve_params("shift_slots") == {
            "oncall_shift_type_id": test_shift_type.id,
            "rotation_shift_type_id": test_shift_type.id,
            "default_shift_type_id": test_shift_type.id,
        }
