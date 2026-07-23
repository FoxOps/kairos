"""
Tests for the automation routes in admin.py.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import AppNotification, Group, OnCall


class TestAutomationDashboard:
    """Tests for /admin/automation."""

    def test_automation_dashboard_get(self, logged_in_client):
        """Test rendering the automation dashboard."""
        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200
        assert b"Automatisation" in response.data or b"Automation" in response.data

    def test_automation_dashboard_unauthenticated(self, client):
        """Test that the automation dashboard requires authentication."""
        response = client.get("/admin/automation", follow_redirects=True)
        assert b"Connexion" in response.data

    def test_dashboard_no_gap_alert_when_none_detected(self, logged_in_client):
        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200
        assert b"Combler ces trous" not in response.data

    def test_dashboard_shows_gap_alert_and_deep_link(self, logged_in_client, test_user):
        """Regression test: an admin ran a refresh with the page's
        default dates (starting today) and concluded nothing happened,
        because a real gap predated that range - the dashboard must
        proactively surface any detected gap with a link that jumps
        straight to the right period, oncall_mode preselected, instead
        of relying on the admin to guess."""
        week1 = date(2024, 1, 5)
        week3 = date(2024, 1, 19)
        for friday in (week1, week3):
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            db.session.add(
                OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
            )
        db.session.commit()

        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200
        assert b"Combler ces trous" in response.data
        assert b"12/01/2024" in response.data
        assert (
            b"start_date=2024-01-12&amp;end_date=2024-01-12&amp;oncall_mode=fill_gaps"
            in response.data
        )


class TestAutomationFull:
    """Tests for /admin/automation/full."""

    def test_automation_full_get(self, logged_in_client):
        """Test rendering the full-automation page."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200
        assert (
            b"astreintes" in response.data.lower()
            or b"oncall" in response.data.lower()
            or b"Automatisation" in response.data
        )

    def test_automation_full_prefills_dates_and_mode_from_query_args(
        self, logged_in_client
    ):
        """Deep-link support for the dashboard's gap alert (see
        TestAutomationDashboard.test_dashboard_shows_gap_alert_and_deep_link)
        - start_date/end_date/oncall_mode passed as query args must
        override the page's own defaults."""
        response = logged_in_client.get(
            "/admin/automation/full"
            "?start_date=2024-01-12&end_date=2024-01-12&oncall_mode=fill_gaps"
        )
        assert response.status_code == 200
        html = response.data.decode()
        assert 'value="2024-01-12"' in html
        assert 'name="oncall_mode" value="fill_gaps" class="radio" checked' in html

    def test_automation_full_ignores_invalid_query_dates(self, logged_in_client):
        """Malformed query-string dates must not crash the page -
        falls back to the normal defaults."""
        response = logged_in_client.get(
            "/admin/automation/full?start_date=not-a-date&end_date=also-not-a-date"
        )
        assert response.status_code == 200

    def test_automation_full_post_save_order(self, logged_in_client, test_user):
        """Test saving the rotation order."""
        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "save_order",
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"ordre" in response.data.lower() or b"Order" in response.data

    def test_automation_full_form_has_single_action_field(self, logged_in_client):
        """Regression test: the form used to also have a static hidden
        field `name="action" value="generate"` alongside the "Generer"
        button - with two `action` fields submitted, Werkzeug only keeps
        the first one (request.form.get always returned "generate",
        never "save_order" or "dry_run" no matter which button was
        clicked). This checks that there is only one `action` field per
        button, carried directly by the button itself
        (name="action" value="...") rather than by a separate
        always-present hidden input."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200
        html = response.data.decode()

        assert 'name="action" value="generate"' in html
        assert 'name="action" value="dry_run"' in html
        # The only place "generate" should appear as an action field
        # value is the button itself (not a separate hidden input that
        # would coexist with the dry_run/save_order buttons).
        assert '<input type="hidden" name="action" value="generate">' not in html

    def test_automation_full_post_dry_run(self, logged_in_client, test_user):
        """Test the dry run of the full automation."""
        today = date.today()
        # Find next Friday
        start_date = today
        while start_date.weekday() != 4:  # Friday
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=7)

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "dry_run",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # Regression test: the dry run used to render a nonexistent
        # template (oncall_dry_run.html), silently replaced by a generic
        # error flash. Checks that the real preview page (on-calls +
        # shifts) is actually rendered.
        assert b"Pr\xc3\xa9visualisation" in response.data
        assert b"Astreintes" in response.data
        assert b"Shifts" in response.data
        # The confirm button must carry the submitted rotation order
        # (a related bug: it used to get lost at confirmation time).
        assert f'name="rotation_order_{test_user.id}"'.encode() in response.data

    def test_automation_full_post_invalid_date(self, logged_in_client, test_user):
        """Test the full automation with invalid dates."""
        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "generate",
                "start_date": "invalid-date",
                "end_date": "invalid-date",
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert (
            b"invalide" in response.data
            or b"invalid" in response.data
            or b"Erreur" in response.data
        )

    def test_automation_full_post_generate_notifies_admins_on_gap(
        self, logged_in_client, test_user, second_user
    ):
        """Regression test: with only 2 rotating users, the legal 2-week
        on-call spacing constraint makes some weeks impossible to fill -
        generate_oncall_schedule() deliberately leaves them unassigned
        rather than violating the constraint, and every admin (here,
        logged_in_client's own "Login User") must get an in-app
        notification about the gap."""
        # logged_in_client's own admin ("Login User") is in an
        # oncall-eligible group too - excluded here so exactly
        # test_user/second_user rotate (a 3rd rotating user could sustain
        # the 2-week spacing indefinitely, masking the gap this test is
        # about).
        with logged_in_client.application.app_context():
            login_group = Group.query.filter_by(name="Test Group Login").first()
            login_group.is_part_of_oncall = False
            db.session.commit()

        today = date.today()
        start_date = today
        while start_date.weekday() != 4:  # Friday
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=35)

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "generate",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
                f"rotation_order_{second_user.id}": "2",
                f"include_{second_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        gap_notifs = AppNotification.query.filter_by(
            notification_type="oncall_generation_gap"
        ).all()
        assert len(gap_notifs) >= 1
        # Deep-links straight to the generation page with the affected
        # period pre-filled and "combler les trous" pre-selected, same
        # convention as the dashboard's own gap-detection banner - not
        # just a plain "/admin/automation" the admin then has to
        # manually re-navigate from.
        assert gap_notifs[0].link.startswith("/admin/automation/full?start_date=")
        assert "oncall_mode=fill_gaps" in gap_notifs[0].link

        # The notification must actually be visible on /notifications
        # for the admin who triggered the generation, not just present
        # in the database - a real user report was that the gap
        # notification "didn't show up" despite the underlying service
        # method being unit-tested in isolation.
        notif_page = logged_in_client.get("/notifications")
        assert notif_page.status_code == 200
        assert b"respecte le d\xc3\xa9lai l\xc3\xa9gal" in notif_page.data

    def test_automation_full_post_generate_notifies_admins_on_shift_unfilled(
        self, logged_in_client, test_user, second_user
    ):
        """Real user report: shift generation can also fail to find
        anyone available for a day (no exception - AdvancedShiftAutomation
        .generate_daily_shifts()'s own "aucun utilisateur disponible"
        business-rule case) and this was never surfaced as an admin
        notification, unlike the equivalent on-call gap case above."""
        from app.models import Leave

        with logged_in_client.application.app_context():
            login_group = Group.query.filter_by(name="Test Group Login").first()
            login_group.is_part_of_schedule = False
            db.session.commit()

        today = date.today()
        target_day = today
        while target_day.weekday() != 0:  # Monday
            target_day += timedelta(days=1)
        end_date = target_day

        with logged_in_client.application.app_context():
            db.session.add_all(
                [
                    Leave(
                        user_id=test_user.id,
                        start_date=target_day,
                        end_date=target_day,
                    ),
                    Leave(
                        user_id=second_user.id,
                        start_date=target_day,
                        end_date=target_day,
                    ),
                ]
            )
            db.session.commit()

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": target_day.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "oncall_mode": "none",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        gap_notifs = AppNotification.query.filter_by(
            notification_type="shift_generation_gap"
        ).all()
        assert len(gap_notifs) >= 1
        assert target_day.strftime("%d/%m/%Y") in gap_notifs[0].message
        assert gap_notifs[0].link.startswith("/admin/automation/full?start_date=")

        notif_page = logged_in_client.get("/notifications")
        assert notif_page.status_code == 200
        assert b"Aucun shift g\xc3\xa9n\xc3\xa9r\xc3\xa9" in notif_page.data


class TestAutomationFullAppendedGeneration:
    """Real admin workflow: run "Générer" once, then run it again for a
    *new*, non-overlapping period appended right after the first one -
    e.g. extending the schedule further into the future once the first
    batch is already committed (no deletion in between, unlike
    oncall_mode="regenerate"). Added after a real report: shifts/
    on-calls generated this way looked fine per the flash messages, but
    the concern was whether the second call correctly sees the first
    call's already-committed data - both for the on-call 2-week spacing
    constraint and for AdvancedShiftAutomation's "was on-call last week"
    07h-15h rotation rule at the exact boundary between the two calls."""

    def test_second_generate_after_first_has_no_gap_and_correct_boundary_rotation(
        self, logged_in_client, test_user, second_user, test_group
    ):
        from app.models import Shift
        from app.models import User as UserModel

        with logged_in_client.application.app_context():
            third_user = UserModel(
                name="Third User",
                email="third-appended@test.com",
                group_id=test_group.id,
            )
            third_user.set_password("test_password")
            db.session.add(third_user)
            db.session.commit()
            third_user_id = third_user.id

        today = date.today()
        first_start = today
        while first_start.weekday() != 4:  # Friday
            first_start += timedelta(days=1)
        first_end = first_start + timedelta(days=7)  # 2 Fridays: F0, F0+7

        rotation_fields = {}
        for position, uid in enumerate(
            [test_user.id, second_user.id, third_user_id], start=1
        ):
            rotation_fields[f"rotation_order_{uid}"] = str(position)
            rotation_fields[f"include_{uid}"] = "1"

        resp1 = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "generate",
                "start_date": first_start.strftime("%Y-%m-%d"),
                "end_date": first_end.strftime("%Y-%m-%d"),
                **rotation_fields,
            },
            follow_redirects=True,
        )
        assert resp1.status_code == 200

        # Appended right after the first call, no overlap, no deletion.
        second_start = first_end + timedelta(days=3)  # the following Monday
        # second_start is a Monday, not a Friday like first_start - a
        # Monday+7 range only crosses a single Friday (+4), so 11 days
        # are needed to capture 2 Fridays (+4 and +11) and stay
        # symmetric with the first call's 2 on-calls.
        second_end = second_start + timedelta(days=11)

        resp2 = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "generate",
                "start_date": second_start.strftime("%Y-%m-%d"),
                "end_date": second_end.strftime("%Y-%m-%d"),
                **rotation_fields,
            },
            follow_redirects=True,
        )
        assert resp2.status_code == 200

        with logged_in_client.application.app_context():
            all_oncalls = OnCall.query.order_by(OnCall.start_time).all()
            # F0, F0+7 (first call) and F0+7+10, F0+7+17 (second call,
            # started the Monday after F0+7's week) - 4 total, no gap
            # between the two calls' Fridays and no spacing violation
            # for whichever user comes back around.
            assert len(all_oncalls) == 4
            for prev, nxt in zip(all_oncalls, all_oncalls[1:], strict=False):
                assert (nxt.start_time - prev.start_time).days == 7

            by_user: dict[int, list] = {}
            for oc in all_oncalls:
                by_user.setdefault(oc.user_id, []).append(oc)
            for _uid, ocs in by_user.items():
                ocs.sort(key=lambda o: o.start_time)
                for prev_oc, next_oc in zip(ocs, ocs[1:], strict=False):
                    gap_days = (next_oc.start_time - prev_oc.end_time).days
                    assert gap_days / 7 >= 2

            # The boundary rotation rule: whoever was on-call the week
            # containing (second_start - 7 days) - which is entirely
            # inside the *first* call's already-committed range - must
            # get the 07h-15h shift on second_start, exactly like within
            # a single call. This is the part that would silently break
            # if shift generation for the second call somehow only saw
            # on-calls created by that same call.
            first_oncall = min(all_oncalls, key=lambda o: o.start_time)
            boundary_shift = Shift.query.filter_by(
                date=second_start, user_id=first_oncall.user_id
            ).first()
            assert boundary_shift is not None
            assert boundary_shift.start_time.hour == 7
            assert boundary_shift.end_time.hour == 15


class TestAutomationStatusMergedIntoDashboard:
    """The old standalone /admin/automation/status page was never linked
    from anywhere in the UI and duplicated 4 of the 5 stats already
    shown on /admin/automation - its one unique piece of information
    (next available on-call date) was folded into the dashboard's own
    stats block instead, and the page was dropped rather than kept as a
    second, unreachable-except-by-URL copy of the same numbers."""

    def test_automation_status_old_url_is_gone(self, logged_in_client):
        response = logged_in_client.get("/admin/automation/status")
        assert response.status_code == 404

    def test_dashboard_shows_next_available_oncall_date(self, logged_in_client):
        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200
        assert (
            b"Prochaine astreinte disponible" in response.data
            or b"Next available on-call" in response.data
        )


class TestRefreshShiftsOldUrlRemoved:
    """The old standalone /admin/automation/refresh-shifts URL was
    dropped outright (not kept as a redirect) when it was merged into
    /admin/automation/full as a "Rafraîchir les shifts" button next to
    Dry Run (see TestAutomationFullRefreshMode below) - user feedback was
    that nobody had it bookmarked/understood it as a separate page, so
    there was nothing worth preserving a redirect for."""

    def test_refresh_shifts_old_url_is_gone(self, logged_in_client):
        response = logged_in_client.get("/admin/automation/refresh-shifts")
        assert response.status_code == 404


class TestAutomationFullRefreshMode:
    """Tests for the "refresh_shifts" action on /admin/automation/full
    (a "Rafraîchir les shifts" button next to Dry Run, replacing the old
    separate /admin/automation/refresh-shifts page - see
    admin_automation_routes.py::automation_full's docstring for why the
    two pages were merged)."""

    def test_refresh_shifts_post(self, logged_in_client):
        """Test refreshing shifts."""
        today = date.today()
        end_date = today + timedelta(days=7)

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": today.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_refresh_shifts_post_invalid_date(self, logged_in_client):
        """Test refreshing shifts with invalid dates."""
        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": "invalid-date",
                "end_date": "invalid-date",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert (
            b"invalide" in response.data
            or b"invalid" in response.data
            or b"Erreur" in response.data
        )


class TestAutomationFullRefreshOncallMode:
    """Tests for the oncall_mode field of the "refresh_shifts" action on
    /admin/automation/full (default "none" leaves on-calls untouched,
    "fill_gaps" only fills empty weeks, "regenerate" fully replaces
    on-calls in the period)."""

    def test_default_mode_does_not_touch_oncalls(self, logged_in_client, test_user):
        """Regression test: omitting oncall_mode entirely must behave
        exactly like the original refresh (shifts only)."""
        today = date.today()
        end_date = today + timedelta(days=7)
        oncall = OnCall(
            user_id=test_user.id,
            start_time=datetime.combine(today, datetime.min.time()),
            end_time=datetime.combine(end_date, datetime.min.time()),
        )
        db.session.add(oncall)
        db.session.commit()
        oncall_id = oncall.id

        logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": today.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
        )

        assert db.session.get(OnCall, oncall_id) is not None

    def test_fill_gaps_mode_creates_missing_oncalls(
        self, logged_in_client, test_user, second_user
    ):
        count_before = OnCall.query.count()
        today = date.today()
        start_date = today
        while start_date.weekday() != 4:
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=14)

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "oncall_mode": "fill_gaps",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert OnCall.query.count() > count_before

    def test_fill_gaps_mode_does_not_touch_existing_oncall(
        self, logged_in_client, test_user, second_user
    ):
        """A manually-assigned on-call must survive a fill_gaps refresh."""
        today = date.today()
        start_date = today
        while start_date.weekday() != 4:
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=14)

        manual_oncall = OnCall(
            user_id=second_user.id,
            start_time=datetime.combine(start_date, datetime.min.time()).replace(
                hour=21
            ),
            end_time=datetime.combine(
                start_date + timedelta(days=7), datetime.min.time()
            ).replace(hour=7),
        )
        db.session.add(manual_oncall)
        db.session.commit()
        manual_id = manual_oncall.id

        logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "oncall_mode": "fill_gaps",
            },
        )

        preserved = db.session.get(OnCall, manual_id)
        assert preserved is not None
        assert preserved.user_id == second_user.id

    def test_regenerate_mode_prefers_existing_valid_assignment(
        self, logged_in_client, test_user, second_user
    ):
        """ "Régénérer entièrement" wipes and recomputes every on-call in
        the period, but now prefers keeping each week's existing
        occupant over blindly replaying the rotation order (minimal-
        perturbation - see OnCallAutomation.capture_existing_assignments()
        and _generate_for_fridays()'s preferred_assignments) - a manual
        assignment that's still valid (no conflict) survives the
        regenerate rather than being needlessly reshuffled. Supersedes
        the old test_regenerate_mode_replaces_oncalls, which asserted
        the opposite (any pre-existing assignment always gets replaced)
        - that was the behavior this feature deliberately changes, not
        a contract worth preserving."""
        today = date.today()
        start_date = today
        while start_date.weekday() != 4:
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=14)

        manual_start_time = datetime.combine(start_date, datetime.min.time()).replace(
            hour=21
        )
        manual_oncall = OnCall(
            user_id=second_user.id,
            start_time=manual_start_time,
            end_time=datetime.combine(
                start_date + timedelta(days=7), datetime.min.time()
            ).replace(hour=7),
        )
        db.session.add(manual_oncall)
        db.session.commit()

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "oncall_mode": "regenerate",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # second_user has no conflict on this week, so they're kept
        # (the row may have been replaced by a freshly generated one
        # reusing the same primary key, so check the assignment, not
        # row survival by id).
        assert (
            OnCall.query.filter_by(
                user_id=second_user.id, start_time=manual_start_time
            ).first()
            is not None
        )

    def test_regenerate_mode_replaces_assignment_with_a_real_conflict(
        self, logged_in_client, test_user, second_user
    ):
        """The minimal-perturbation preference is not a special case:
        a preferred user with a real conflict on that exact week (here,
        their own leave) is filtered out like any other candidate -
        regenerate must still fall back to a valid rotation-order
        candidate instead of leaving the week unfillable."""
        from app.models import Leave

        # logged_in_client's own admin ("Login User") is in an
        # oncall-eligible group too - excluded here so exactly
        # test_user/second_user are the eligible pool, same pattern as
        # TestAutomationFull.test_automation_full_post_generate_notifies_admins_on_gap.
        login_group = Group.query.filter_by(name="Test Group Login").first()
        login_group.is_part_of_oncall = False
        db.session.commit()

        today = date.today()
        start_date = today
        while start_date.weekday() != 4:
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=14)

        manual_start_time = datetime.combine(start_date, datetime.min.time()).replace(
            hour=21
        )
        manual_oncall = OnCall(
            user_id=second_user.id,
            start_time=manual_start_time,
            end_time=datetime.combine(
                start_date + timedelta(days=7), datetime.min.time()
            ).replace(hour=7),
        )
        db.session.add(manual_oncall)
        db.session.add(
            Leave(
                user_id=second_user.id,
                start_date=start_date,
                end_date=start_date + timedelta(days=6),
            )
        )
        db.session.commit()

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "refresh_shifts",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "oncall_mode": "regenerate",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert (
            OnCall.query.filter_by(
                user_id=second_user.id, start_time=manual_start_time
            ).first()
            is None
        )
        assert (
            OnCall.query.filter_by(
                user_id=test_user.id, start_time=manual_start_time
            ).first()
            is not None
        )
