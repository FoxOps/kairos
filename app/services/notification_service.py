"""
Notification service for Leviia Schedule.

Business logic for the weekly email reminders (shifts + on-call). Called
by the standalone scripts (scripts/send_shift_notifications.py,
scripts/send_oncall_notifications.py), themselves triggered by cron - not
by any Flask route. Config (SMTP, enabled flag) is passed in rather than
imported here, since it lives in scripts/notification_config.py and app/
code should not depend on scripts/.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from flask import render_template

from app import db
from app.models import NotificationLog, User
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.utils.notifications import send_email


@dataclass
class NotificationBatchResult:
    """Summary of a batch send, for logging on the script side."""

    sent: list[str] = field(default_factory=list)
    skipped_already_sent: list[str] = field(default_factory=list)
    skipped_disabled_by_user: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


class NotificationService:
    """Business logic for the weekly email notifications."""

    SHIFT_WEEKLY = "shift_weekly"
    ONCALL_WEEKLY = "oncall_weekly"

    @staticmethod
    def next_monday(reference_date: date | None = None) -> date:
        """Next Monday strictly after reference_date (today by default).
        Always in the future, even if reference_date is already a Monday -
        this avoids a manual run on a Monday targeting the current week
        instead of the next one."""
        today = reference_date or date.today()
        days_ahead = (0 - today.weekday()) % 7
        return today + timedelta(days=days_ahead or 7)

    @staticmethod
    def next_friday(reference_date: date | None = None) -> date:
        """Next Friday strictly after reference_date."""
        today = reference_date or date.today()
        days_ahead = (4 - today.weekday()) % 7
        return today + timedelta(days=days_ahead or 7)

    @staticmethod
    def send_weekly_shift_notifications(
        smtp_config: dict,
        app_base_url: str | None = None,
        reference_date: date | None = None,
    ) -> NotificationBatchResult:
        """
        Send a summary email to each user who has at least one shift next
        week (Monday-Friday). One email per user per week (NotificationLog
        prevents duplicates if the script is re-run).
        """
        result = NotificationBatchResult()

        week_start = NotificationService.next_monday(reference_date)
        week_end = week_start + timedelta(days=4)

        shifts = ShiftRepository.list_in_date_range_with_user(week_start, week_end)
        shifts_by_user: dict[int, list] = defaultdict(list)
        for shift in shifts:
            shifts_by_user[shift.user_id].append(shift)

        for user_id, user_shifts in shifts_by_user.items():
            user = user_shifts[0].user
            if not user.shift_notifications_enabled:
                result.skipped_disabled_by_user.append(user.email)
                continue
            if NotificationLog.already_sent(
                user_id, NotificationService.SHIFT_WEEKLY, week_start
            ):
                result.skipped_already_sent.append(user.email)
                continue

            try:
                html_body = render_template(
                    "emails/shift_weekly.html",
                    user_name=user.name,
                    week_start=week_start,
                    week_end=week_end,
                    shifts=user_shifts,
                    app_base_url=app_base_url,
                )
                text_body = render_template(
                    "emails/shift_weekly.txt",
                    user_name=user.name,
                    week_start=week_start,
                    week_end=week_end,
                    shifts=user_shifts,
                    app_base_url=app_base_url,
                )
                send_email(
                    to_email=user.email,
                    subject=(
                        f"Vos shifts de la semaine du "
                        f"{week_start.strftime('%d/%m')} au {week_end.strftime('%d/%m')}"
                    ),
                    html_body=html_body,
                    text_body=text_body,
                    **smtp_config,
                )
            except Exception as e:
                result.failed.append((user.email, str(e)))
                continue

            db.session.add(
                NotificationLog(
                    user_id=user_id,
                    notification_type=NotificationService.SHIFT_WEEKLY,
                    period_start=week_start,
                )
            )
            db.session.commit()
            result.sent.append(user.email)

        return result

    @staticmethod
    def send_weekly_oncall_notification(
        smtp_config: dict,
        app_base_url: str | None = None,
        reference_date: date | None = None,
    ) -> NotificationBatchResult:
        """
        Send an email to the on-call user for the period starting the
        upcoming Friday at 9pm.
        """
        result = NotificationBatchResult()

        oncall_friday = NotificationService.next_friday(reference_date)
        oncall_start = datetime.combine(oncall_friday, time(21, 0))
        oncall_end = oncall_start + timedelta(days=7, hours=-14)

        oncall = OnCallRepository.get_starting_at(oncall_start)
        if oncall is None:
            return result

        user: User = oncall.user
        if not user.oncall_notifications_enabled:
            result.skipped_disabled_by_user.append(user.email)
            return result
        if NotificationLog.already_sent(
            user.id, NotificationService.ONCALL_WEEKLY, oncall_friday
        ):
            result.skipped_already_sent.append(user.email)
            return result

        try:
            html_body = render_template(
                "emails/oncall_weekly.html",
                user_name=user.name,
                oncall_start=oncall_start,
                oncall_end=oncall_end,
                app_base_url=app_base_url,
            )
            text_body = render_template(
                "emails/oncall_weekly.txt",
                user_name=user.name,
                oncall_start=oncall_start,
                oncall_end=oncall_end,
                app_base_url=app_base_url,
            )
            send_email(
                to_email=user.email,
                subject=f"Astreinte du {oncall_start.strftime('%d/%m/%Y')}",
                html_body=html_body,
                text_body=text_body,
                **smtp_config,
            )
        except Exception as e:
            result.failed.append((user.email, str(e)))
            return result

        db.session.add(
            NotificationLog(
                user_id=user.id,
                notification_type=NotificationService.ONCALL_WEEKLY,
                period_start=oncall_friday,
            )
        )
        db.session.commit()
        result.sent.append(user.email)

        return result
