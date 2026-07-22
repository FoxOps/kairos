"""Runs djlint (Jinja/HTML linter, config: .djlint.toml at the repo
root) against app/templates/ as part of the normal test suite, not just
`make lint` - a broken/inconsistent template should fail `pytest
tests/` the same way a Ruff violation fails it, not require a separate
command an author has to remember to run."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = REPO_ROOT / "app" / "templates"


def test_templates_pass_djlint():
    result = subprocess.run(
        [sys.executable, "-m", "djlint", str(TEMPLATES_DIR)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "djlint found issues in app/templates/ "
        "(see .djlint.toml for the project's rule/per-file ignores):\n"
        f"{result.stdout}\n{result.stderr}"
    )
