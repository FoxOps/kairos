"""Direct tests for app/utils/helpers/pagination_helpers.py::resolve_per_page's
branches not exercised via the /schedule /oncall /leave route-level tests."""

from app.utils.helpers.pagination_helpers import _UNLIMITED, resolve_per_page


class _FakeArgs:
    def __init__(self, value):
        self._value = value

    def get(self, key, default=None, type=None):
        if self._value is None:
            return default
        return type(self._value) if type else self._value


class TestResolvePerPage:
    def test_already_unlimited_sentinel_stays_unlimited(self, test_app):
        with test_app.app_context():
            assert resolve_per_page(_FakeArgs(_UNLIMITED)) == _UNLIMITED

    def test_value_outside_options_falls_back_to_default(self, test_app):
        with test_app.app_context():
            from app.services import SettingsService

            default = SettingsService.get_items_per_page()
            assert resolve_per_page(_FakeArgs(7)) == default
