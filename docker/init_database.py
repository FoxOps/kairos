#!/usr/bin/env python3
"""SQLite database initialization script for Kairos."""

from app import app
from run import create_default_data, setup_database


def main():
    """Initializes the database schema and default data.

    Real security bug found and fixed here: this script used to build
    its own group/shift-type/admin rows by hand, calling
    `set_password()` with the same fixed literal every install ships in
    .env.example as a documented quick-start convenience value - with
    no DEFAULT_ADMIN_PASSWORD override and no must_change_password flag.
    That meant every Docker deployment got that exact same password
    unconditionally, never forced to change, regardless of what an
    operator set in their own .env (the hardcoded call never even read
    it). This had silently diverged from run.py's own
    create_default_data() (used by the non-Docker `python run.py`
    path), which already handles the group/shift-type/admin creation
    correctly (env-var-overridable email/password, forces a change on
    first login) - delegating to it here, instead of duplicating and
    re-diverging from that logic, is the actual fix."""
    with app.app_context():
        setup_database()
        create_default_data()


if __name__ == "__main__":
    main()
