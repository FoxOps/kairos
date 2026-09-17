"""Regression test for a real security bug found in production QA:
docker/init_database.py used to build its own group/shift-type/admin
rows by hand, hardcoding `admin.set_password("admin123")` with no
DEFAULT_ADMIN_PASSWORD override and no must_change_password flag -
every Docker deployment shipped the exact same publicly-documented
password, never forced to change, regardless of what an operator set
in their own .env (the hardcoded call never even read that env var).
This had silently diverged from run.py's own create_default_data()
(used by the non-Docker `python run.py` path), which already handled
this correctly. Fixed by making docker/init_database.py delegate to
create_default_data() instead of duplicating and re-diverging from it.

Source-inspection test (same pattern as
test_run_functions.py::TestDevServerDebugFlag and
test_backup_database.py::test_no_import_of_app_package) rather than
actually invoking main() - docker/init_database.py imports the real
production `app` object (not TestingConfig), so exercising it directly
here would require standing up production config in the test suite for
no real benefit: the group/shift-type/admin creation logic itself is
already covered by test_run_functions.py::TestCreateDefaultData against
the exact same create_default_data() function this script now calls."""

import ast
import os


def _path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docker",
        "init_database.py",
    )


def _read_source() -> str:
    with open(_path()) as f:
        return f.read()


def _call_names(source: str) -> set[str]:
    """Every function/method name actually CALLED in the code, e.g.
    `foo.set_password(...)` -> "set_password" - parsed via `ast`
    instead of substring-matching, since this file's own docstring
    describes the old bug in prose and would otherwise trip a naive
    text search on the very call it's warning against."""
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                names.add(node.func.id)
    return names


class TestDockerInitDatabaseDelegatesToSharedBootstrap:
    def test_no_hardcoded_password(self):
        calls = _call_names(_read_source())
        # A hardcoded bootstrap would call User(...) and .set_password(...)
        # directly - the fixed version only ever calls setup_database()/
        # create_default_data(), never builds a User itself.
        assert "set_password" not in calls
        assert "User" not in calls

    def test_delegates_to_create_default_data(self):
        source = _read_source()
        assert "from run import create_default_data, setup_database" in source
        calls = _call_names(source)
        assert "create_default_data" in calls
        assert "setup_database" in calls
