"""
Tests for app/services/notification_service.py.
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from app import db
from app.models import NotificationLog, OnCall, Shift
from app.services import NotificationService

SMTP_CONFIG = {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "from_email": "noreply@kairos.local",
    "smtp_username": None,
    "smtp_password": None,
    "smtp_use_tls": True,
    "smtp_timeout": 10,
}


class TestNextMonday:
    def test_from_sunday_gives_next_day(self):
        sunday = date(2026, 7, 12)
        assert NotificationService.next_monday(sunday) == date(2026, 7, 13)

    def test_from_monday_gives_next_week_not_today(self):
        monday = date(2026, 7, 13)
        assert NotificationService.next_monday(monday) == date(2026, 7, 20)

    def test_from_wednesday(self):
        wednesday = date(2026, 7, 15)
        assert NotificationService.next_monday(wednesday) == date(2026, 7, 20)


class TestNextFriday:
    def test_from_thursday_gives_next_day(self):
        thursday = date(2026, 7, 9)
        assert NotificationService.next_friday(thursday) == date(2026, 7, 10)

    def test_from_friday_gives_next_week_not_today(self):
        friday = date(2026, 7, 10)
        assert NotificationService.next_friday(friday) == date(2026, 7, 17)


class TestWeekEndForStart:
    """_week_end_for_start() replaces send_weekly_shift_notifications()'s
    former hardcoded week_start + 4 days (always "Friday", regardless of
    the configurable WeekendDefinitionRule)."""

    def test_default_weekend_gives_friday(self, test_app):
        monday = date(2026, 7, 13)
        assert NotificationService._week_end_for_start(monday) == date(2026, 7, 17)

    def test_custom_weekend_thu_through_sun_gives_wednesday(self, test_app):
        """weekend_days replaces the default [5, 6] entirely, it doesn't
        add to it - a Thursday-Sunday weekend means Monday-Wednesday is
        the actual work week here."""
        from app.models.automation_rule import AutomationRule

        AutomationRule.set("weekend_definition", {"weekend_days": [3, 4, 5, 6]})
        db.session.commit()

        monday = date(2026, 7, 13)
        assert NotificationService._week_end_for_start(monday) == date(2026, 7, 15)


class TestSendWeeklyShiftNotifications:
    def test_sends_one_email_per_user_with_shifts(
        self, test_app, test_group, test_user, second_user, test_shift_type
    ):
        with test_app.app_context():
            monday = NotificationService.next_monday(date(2026, 7, 12))
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=datetime.combine(monday, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(monday, datetime.min.time()).replace(hour=15),
                date=monday,
            )
            db.session.add(shift)
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            assert result.sent == [test_user.email]
            assert result.failed == []
            instance.sendmail.assert_called_once()

    def test_user_without_shifts_gets_no_email(
        self, test_app, test_group, test_user, second_user
    ):
        with test_app.app_context():
            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            assert result.sent == []
            instance.sendmail.assert_not_called()

    def test_idempotent_does_not_resend_same_week(
        self, test_app, test_group, test_user, test_shift_type
    ):
        with test_app.app_context():
            monday = NotificationService.next_monday(date(2026, 7, 12))
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=datetime.combine(monday, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(monday, datetime.min.time()).replace(hour=15),
                date=monday,
            )
            db.session.add(shift)
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )
                result2 = NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            assert result2.sent == []
            assert result2.skipped_already_sent == [test_user.email]
            assert instance.sendmail.call_count == 1

    def test_smtp_failure_is_logged_and_does_not_block_others(
        self, test_app, test_group, test_user, second_user, test_shift_type
    ):
        with test_app.app_context():
            monday = NotificationService.next_monday(date(2026, 7, 12))
            for user in (test_user, second_user):
                db.session.add(
                    Shift(
                        user_id=user.id,
                        shift_type_id=test_shift_type.id,
                        start_time=datetime.combine(
                            monday, datetime.min.time()
                        ).replace(hour=7),
                        end_time=datetime.combine(monday, datetime.min.time()).replace(
                            hour=15
                        ),
                        date=monday,
                    )
                )
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                instance.sendmail.side_effect = [OSError("boom"), None]
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            assert len(result.failed) == 1
            assert len(result.sent) == 1
            # A NotificationLog row should only exist for the successful send.
            assert NotificationLog.query.count() == 1

    def test_user_with_notifications_disabled_is_skipped(
        self, test_app, test_group, test_user, test_shift_type
    ):
        with test_app.app_context():
            test_user.shift_notifications_enabled = False
            monday = NotificationService.next_monday(date(2026, 7, 12))
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=datetime.combine(monday, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(monday, datetime.min.time()).replace(hour=15),
                date=monday,
            )
            db.session.add(shift)
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            assert result.sent == []
            assert result.skipped_disabled_by_user == [test_user.email]
            instance.sendmail.assert_not_called()
            # No NotificationLog row - nothing was sent, so re-enabling
            # mid-week and rerunning the script must be able to catch up.
            assert NotificationLog.query.count() == 0

    def test_success_relays_to_selected_apprise_targets(
        self, test_app, test_group, test_user, test_shift_type
    ):
        with test_app.app_context():
            test_user.set_apprise_shift_target_ids([42])
            monday = NotificationService.next_monday(date(2026, 7, 12))
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=datetime.combine(monday, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(monday, datetime.min.time()).replace(hour=15),
                date=monday,
            )
            db.session.add(shift)
            db.session.commit()

            with (
                patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp,
                patch(
                    "app.services.notification_service.AppriseNotificationService."
                    "notify_to_targets"
                ) as mock_notify,
            ):
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            assert mock_notify.call_args[0][0] == [42]

    def test_no_targets_selected_skips_relay(
        self, test_app, test_group, test_user, test_shift_type
    ):
        with test_app.app_context():
            monday = NotificationService.next_monday(date(2026, 7, 12))
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=datetime.combine(monday, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(monday, datetime.min.time()).replace(hour=15),
                date=monday,
            )
            db.session.add(shift)
            db.session.commit()

            with (
                patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp,
                patch(
                    "app.services.notification_service.AppriseNotificationService."
                    "notify_to_targets"
                ) as mock_notify,
            ):
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            mock_notify.assert_not_called()


class TestSendWeeklyOncallNotification:
    def test_sends_to_assigned_user(self, test_app, test_group, test_user):
        with test_app.app_context():
            thursday = date(2026, 7, 9)
            friday = NotificationService.next_friday(thursday)
            start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            assert result.sent == [test_user.email]
            instance.sendmail.assert_called_once()

    def test_no_oncall_assigned_sends_nothing(self, test_app, test_group):
        with test_app.app_context():
            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=date(2026, 7, 9)
                )

            assert result.sent == []
            assert result.failed == []
            instance.sendmail.assert_not_called()

    def test_user_with_notifications_disabled_is_skipped(
        self, test_app, test_group, test_user
    ):
        with test_app.app_context():
            test_user.oncall_notifications_enabled = False
            thursday = date(2026, 7, 9)
            friday = NotificationService.next_friday(thursday)
            start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            assert result.sent == []
            assert result.skipped_disabled_by_user == [test_user.email]
            instance.sendmail.assert_not_called()

    def test_idempotent_does_not_resend_same_week(
        self, test_app, test_group, test_user
    ):
        with test_app.app_context():
            thursday = date(2026, 7, 9)
            friday = NotificationService.next_friday(thursday)
            start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )
                result2 = NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            assert result2.sent == []
            assert result2.skipped_already_sent == [test_user.email]
            assert instance.sendmail.call_count == 1


class TestSendWeeklyOncallNotificationGroupAndAnchorAware:
    """Regression coverage for two real bugs found in code review:
    (1) get_starting_at() was called unscoped, so in oncall_scheduling_mode
    "per_group" only one of two concurrent on-calls (for different
    groups) ever got its reminder sent - the other was silently
    skipped, no error. (2) the anchor day/hours were hardcoded to
    Friday 21:00-07:00 regardless of a configured OnCallAnchorRule, so
    a customized anchor made this function look for an on-call that
    would never match, silently sending nothing."""

    def test_per_group_mode_sends_to_both_groups_concurrent_oncalls(
        self, test_app, test_group
    ):
        from app.models import Group, User
        from app.services import SettingsService

        with test_app.app_context():
            other_group = Group(
                name="Other Oncall Group",
                is_part_of_schedule=True,
                is_part_of_oncall=True,
            )
            db.session.add(other_group)
            db.session.commit()

            user_a = User(
                name="Group A User",
                email="group-a-oncall@test.com",
                group_id=test_group.id,
            )
            user_a.set_password("x")
            user_b = User(
                name="Group B User",
                email="group-b-oncall@test.com",
                group_id=other_group.id,
            )
            user_b.set_password("x")
            db.session.add_all([user_a, user_b])
            db.session.commit()

            SettingsService.set_oncall_scheduling_mode("per_group")

            thursday = date(2026, 7, 9)
            friday = NotificationService.next_friday(thursday)
            start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            # Two concurrent on-calls for the same week, one per group -
            # only possible/meaningful in per_group mode.
            db.session.add(OnCall(user_id=user_a.id, start_time=start, end_time=end))
            db.session.add(OnCall(user_id=user_b.id, start_time=start, end_time=end))
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            assert set(result.sent) == {user_a.email, user_b.email}
            assert instance.sendmail.call_count == 2

    def test_custom_anchor_is_respected(self, test_app, test_group, test_user):
        from app.models.automation_rule import AutomationRule

        with test_app.app_context():
            # Monday 09:00 -> Monday 17:00 one week later, instead of
            # the default Friday 21:00 -> Friday 07:00.
            AutomationRule.set(
                "oncall_anchor",
                {"weekday": 0, "start_hour": 9, "end_hour": 17},
            )
            db.session.commit()

            thursday = date(2026, 7, 9)
            monday = thursday + timedelta(days=(0 - thursday.weekday()) % 7 or 7)
            start = datetime.combine(monday, datetime.min.time()).replace(hour=9)
            end = start + timedelta(days=7, hours=-16)
            db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
            db.session.commit()

            with patch(
                "app.utils.notifications.email_sender.smtplib.SMTP"
            ) as mock_smtp:
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                result = NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            assert result.sent == [test_user.email]
            instance.sendmail.assert_called_once()


class TestSendWeeklyOncallApprise:
    def test_success_relays_to_selected_apprise_targets(
        self, test_app, test_group, test_user
    ):
        with test_app.app_context():
            test_user.set_apprise_oncall_target_ids([7])
            thursday = date(2026, 7, 9)
            friday = NotificationService.next_friday(thursday)
            start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
            db.session.commit()

            with (
                patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp,
                patch(
                    "app.services.notification_service.AppriseNotificationService."
                    "notify_to_targets"
                ) as mock_notify,
            ):
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            assert mock_notify.call_args[0][0] == [7]

    def test_no_targets_selected_skips_relay(self, test_app, test_group, test_user):
        with test_app.app_context():
            thursday = date(2026, 7, 9)
            friday = NotificationService.next_friday(thursday)
            start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
            db.session.commit()

            with (
                patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp,
                patch(
                    "app.services.notification_service.AppriseNotificationService."
                    "notify_to_targets"
                ) as mock_notify,
            ):
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            mock_notify.assert_not_called()
