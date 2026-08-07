"""Direct tests for app/utils/helpers/pagination_helpers.py::resolve_per_page's
branches not exercised via the /schedule /oncall /leave route-level tests."""

from datetime import date

from app.utils.helpers.pagination_helpers import (
    _UNLIMITED,
    parse_date_range_filter,
    resolve_per_page,
)


class _FakeArgs:
    def __init__(self, value):
        self._value = value

    def get(self, key, default=None, type=None):
        if self._value is None:
            return default
        return type(self._value) if type else self._value


class _FakeMultiArgs:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None, type=None):
        value = self._values.get(key, default)
        return type(value) if type and value is not None else value


class TestResolvePerPage:
    def test_already_unlimited_sentinel_stays_unlimited(self, test_app):
        with test_app.app_context():
            assert resolve_per_page(_FakeArgs(_UNLIMITED)) == _UNLIMITED

    def test_value_outside_options_falls_back_to_default(self, test_app):
        with test_app.app_context():
            from app.services import SettingsService

            default = SettingsService.get_items_per_page()
            assert resolve_per_page(_FakeArgs(7)) == default


class TestParseDateRangeFilter:
    def test_both_valid(self):
        result = parse_date_range_filter(
            _FakeMultiArgs(date_from="2026-01-01", date_to="2026-01-31")
        )
        assert result == (
            date(2026, 1, 1),
            date(2026, 1, 31),
            "2026-01-01",
            "2026-01-31",
        )

    def test_both_empty(self):
        assert parse_date_range_filter(_FakeMultiArgs()) == (None, None, "", "")

    def test_valid_date_from_with_malformed_date_to_keeps_date_from(self):
        """Regression test: a single try/except around both parses used
        to null out date_from too whenever date_to alone was malformed."""
        result = parse_date_range_filter(
            _FakeMultiArgs(date_from="2026-01-01", date_to="not-a-date")
        )
        assert result == (date(2026, 1, 1), None, "2026-01-01", "")

    def test_malformed_date_from_with_valid_date_to_keeps_date_to(self):
        result = parse_date_range_filter(
            _FakeMultiArgs(date_from="not-a-date", date_to="2026-01-31")
        )
        assert result == (None, date(2026, 1, 31), "", "2026-01-31")
