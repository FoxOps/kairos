"""
Shared query-args filter schemas for the public API's list endpoints
(shifts, oncall, leave, users). start/end use overlap semantics against
the underlying resource's own date span, matching the exact same
comparisons ShiftRepository/OnCallRepository/LeaveRepository._filtered_query()
already apply - a shift/on-call/leave that starts before the requested
range but continues into it is still returned. All three repositories
already take `date_from`/`date_to` as plain dates (not datetimes), so
these filters are typed the same way rather than inventing a new
timezone-aware representation the repositories don't accept.
"""

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class DateRangeFilterMixin(Schema):
    start = fields.Date(
        load_default=None,
        metadata={
            "description": "Only include results overlapping on or "
            "after this date (inclusive)."
        },
    )
    end = fields.Date(
        load_default=None,
        metadata={
            "description": "Only include results overlapping on or "
            "before this date (inclusive)."
        },
    )

    @validates_schema
    def validate_range(self, data, **kwargs):
        start = data.get("start")
        end = data.get("end")
        if start is not None and end is not None and start > end:
            raise ValidationError(
                {"start": ["start must not be after end."]}, field_name="start"
            )


class UserGroupFilterMixin(Schema):
    user_id = fields.Int(
        load_default=None,
        validate=validate.Range(min=1),
        metadata={"description": "Only include results for this user."},
    )
    group_id = fields.Int(
        load_default=None,
        validate=validate.Range(min=1),
        metadata={"description": "Only include results for this group."},
    )
