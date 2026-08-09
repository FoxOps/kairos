"""
Notification service for Kairos.

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
from flask_babel import force_locale
from flask_babel import gettext as _

from app import db
from app.models import Group, NotificationLog, User
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.apprise_notification_service import AppriseNotificationService
from app.services.settings_service import SettingsService
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
    def _week_end_for_start(week_start: date, group=None) -> date:
        """Last non-weekend day in the 7-day window starting at
        week_start, per the configurable WeekendDefinitionRule -
        replaces a previously hardcoded `week_start + 4 days` ("always
        Friday") that ignored a customized weekend definition. Falls
        back to the hardcoded Friday shape only in the degenerate case
        where every day of the week is configured as "weekend" (not
        rejected by WeekendDefinitionRule.validate_params(), but not a
        sane configuration either)."""
        from app.utils.automation.rules import WeekendDefinitionRule

        for offset in range(6, -1, -1):
            candidate = week_start + timedelta(days=offset)
            if not WeekendDefinitionRule.is_weekend(candidate, group=group):
                return candidate
        return week_start + timedelta(days=4)

    @staticmethod
    def _next_anchor_date(reference_date: date, weekday: int) -> date:
        """Next date strictly after reference_date whose weekday() ==
        weekday - generalizes next_friday() for an arbitrary configured
        OnCallAnchorRule weekday (next_friday() itself stays as the
        tested, public helper for the default-anchor case)."""
        days_ahead = (weekday - reference_date.weekday()) % 7
        return reference_date + timedelta(days=days_ahead or 7)

    @staticmethod
    def _log_sent_and_relay(
        user: User,
        notification_type: str,
        period_start: date,
        apprise_target_ids: list[int],
        subject: str,
        text_body: str,
        result: NotificationBatchResult,
    ) -> None:
        """Shared tail of both weekly sends: write the NotificationLog
        idempotency guard, then relay to the recipient's own picked
        Apprise targets (if any)."""
        db.session.add(
            NotificationLog(
                user_id=user.id,
                notification_type=notification_type,
                period_start=period_start,
            )
        )
        db.session.commit()
        result.sent.append(user.email)

        if apprise_target_ids:
            AppriseNotificationService.notify_to_targets(
                apprise_target_ids, subject, text_body
            )

    @staticmethod
    def send_weekly_shift_notifications(
        smtp_config: dict,
        app_base_url: str | None = None,
        reference_date: date | None = None,
    ) -> NotificationBatchResult:
        """
        Send a summary email to each user who has at least one shift next
        week (Monday through the last working day per the configurable
        WeekendDefinitionRule - org-wide, since this is one summary
        window shared across every recipient, not per-recipient). One
        email per user per week (NotificationLog prevents duplicates if
        the script is re-run).
        """
        result = NotificationBatchResult()

        week_start = NotificationService.next_monday(reference_date)
        week_end = NotificationService._week_end_for_start(week_start)

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
                with force_locale(user.effective_language()):
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
                    subject = _(
                        "Vos shifts de la semaine du %(start)s au %(end)s",
                        start=week_start.strftime("%d/%m"),
                        end=week_end.strftime("%d/%m"),
                    )
                send_email(
                    to_email=user.email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    **smtp_config,
                )
            except Exception as e:
                result.failed.append((user.email, str(e)))
                continue

            NotificationService._log_sent_and_relay(
                user,
                NotificationService.SHIFT_WEEKLY,
                week_start,
                user.get_apprise_shift_target_ids(),
                subject,
                text_body,
                result,
            )

        if result.failed:
            AppriseNotificationService.notify(
                "system",
                _("Échecs d'envoi des rappels de shifts"),
                _(
                    "%(count)s email(s) de rappel de shifts n'ont pas pu être "
                    "envoyés cette semaine.",
                    count=len(result.failed),
                ),
            )

        return result

    @staticmethod
    def send_weekly_oncall_notification(
        smtp_config: dict,
        app_base_url: str | None = None,
        reference_date: date | None = None,
    ) -> NotificationBatchResult:
        """
        Send an email to the on-call user for the period starting at the
        next occurrence of the configured on-call anchor
        (OnCallAnchorRule - Friday 21:00 by default, but admin-
        configurable, org-wide or per Group - previously hardcoded here,
        so a customized anchor made this function look for an on-call
        that would never match, silently sending nothing).

        In oncall_scheduling_mode="per_group" (SettingsService), runs
        once per oncall-eligible Group instead of a single unscoped
        lookup - two groups can have a genuinely concurrent on-call for
        the same week in that mode (see OnCallRepository.get_starting_at()'s
        own docstring), and an unscoped lookup previously meant only one
        of them ever got notified, the other silently skipped.
        """
        from app.utils.automation.rules import OnCallAnchorRule

        result = NotificationBatchResult()
        reference = reference_date or date.today()

        oncall_per_group = SettingsService.get_oncall_scheduling_mode() == "per_group"
        oncall_groups = (
            Group.query.filter_by(is_part_of_oncall=True).all()
            if oncall_per_group
            else [None]
        )

        for group in oncall_groups:
            anchor = OnCallAnchorRule.resolve(group=group)
            oncall_day = NotificationService._next_anchor_date(
                reference, anchor["weekday"]
            )
            oncall_start = datetime.combine(oncall_day, time(anchor["start_hour"]))
            oncall_end = datetime.combine(
                oncall_day + timedelta(days=7), time(anchor["end_hour"])
            )

            oncall = OnCallRepository.get_starting_at(
                oncall_start, group_id=group.id if group is not None else None
            )
            if oncall is None:
                continue

            user: User = oncall.user
            if not user.oncall_notifications_enabled:
                result.skipped_disabled_by_user.append(user.email)
                continue
            if NotificationLog.already_sent(
                user.id, NotificationService.ONCALL_WEEKLY, oncall_day
            ):
                result.skipped_already_sent.append(user.email)
                continue

            try:
                with force_locale(user.effective_language()):
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
                    subject = _(
                        "Astreinte du %(date)s", date=oncall_start.strftime("%d/%m/%Y")
                    )
                send_email(
                    to_email=user.email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    **smtp_config,
                )
            except Exception as e:
                result.failed.append((user.email, str(e)))
                AppriseNotificationService.notify(
                    "system",
                    _("Échec d'envoi du rappel d'astreinte"),
                    _(
                        "Le rappel d'astreinte pour %(email)s n'a pas pu être envoyé.",
                        email=user.email,
                    ),
                )
                continue

            NotificationService._log_sent_and_relay(
                user,
                NotificationService.ONCALL_WEEKLY,
                oncall_day,
                user.get_apprise_oncall_target_ids(),
                subject,
                text_body,
                result,
            )

        return result
