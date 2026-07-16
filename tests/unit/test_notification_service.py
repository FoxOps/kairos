"""
Tests pour app/services/notification_service.py.
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from app import db
from app.models import NotificationLog, OnCall, Shift
from app.services import NotificationService

SMTP_CONFIG = {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "from_email": "noreply@leviia.local",
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

    def test_success_relays_to_apprise_shift_weekly_category(
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
                    "app.services.notification_service.AppriseNotificationService.notify"
                ) as mock_notify,
            ):
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_shift_notifications(
                    SMTP_CONFIG, reference_date=date(2026, 7, 12)
                )

            assert mock_notify.call_args[0][0] == "shift_weekly"

    def test_apprise_toggle_off_skips_relay(
        self, test_app, test_group, test_user, test_shift_type
    ):
        with test_app.app_context():
            test_user.apprise_shift_notifications_enabled = False
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
                    "app.services.notification_service.AppriseNotificationService.notify"
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


class TestSendWeeklyOncallApprise:
    def test_success_relays_to_apprise_oncall_weekly_category(
        self, test_app, test_group, test_user
    ):
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
                    "app.services.notification_service.AppriseNotificationService.notify"
                ) as mock_notify,
            ):
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            assert mock_notify.call_args[0][0] == "oncall_weekly"

    def test_apprise_toggle_off_skips_relay(self, test_app, test_group, test_user):
        with test_app.app_context():
            test_user.apprise_oncall_notifications_enabled = False
            thursday = date(2026, 7, 9)
            friday = NotificationService.next_friday(thursday)
            start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
            db.session.commit()

            with (
                patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp,
                patch(
                    "app.services.notification_service.AppriseNotificationService.notify"
                ) as mock_notify,
            ):
                instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = instance
                NotificationService.send_weekly_oncall_notification(
                    SMTP_CONFIG, reference_date=thursday
                )

            mock_notify.assert_not_called()
