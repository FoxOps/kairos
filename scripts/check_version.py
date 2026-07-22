#!/usr/bin/env python3
"""
Verify that the current git tag and the app's own APP_VERSION_DEFAULT
(app/utils/health.py) agree, per Docs/reference/VERSIONING.md. Meant to
be run right before/after tagging a release - not on every commit,
since it requires HEAD to be exactly on a tag.

Comparison is case-insensitive: git tags/branches for a release
conventionally use uppercase ("1.0.0-RC4") while APP_VERSION_DEFAULT
is required to stay lowercase ("1.0.0-rc4") per SemVer's own
pre-release convention - see Docs/reference/VERSIONING.md for why this
is a documented, intentional mapping rather than something either side
should be "fixed" to match byte-for-byte.

Usage:
    python scripts/check_version.py
    make check-version
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def current_tag() -> str | None:
    result = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def app_version() -> str | None:
    content = (ROOT / "app/utils/health.py").read_text()
    match = re.search(r'APP_VERSION_DEFAULT = "([^"]+)"', content)
    return match.group(1) if match else None


def main() -> int:
    tag = current_tag()
    if tag is None:
        print(
            "HEAD isn't exactly on a git tag - nothing to check. Run this "
            "right after tagging a release, not on an arbitrary commit.",
            file=sys.stderr,
        )
        return 1

    version = app_version()
    if version is None:
        print(
            "Could not read APP_VERSION_DEFAULT from app/utils/health.py.",
            file=sys.stderr,
        )
        return 1

    if tag.lower() != version.lower():
        print(
            f"Mismatch: git tag '{tag}' does not match "
            f"APP_VERSION_DEFAULT '{version}' (case-insensitive compare). "
            "Fix app/utils/health.py or re-tag before publishing.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: tag '{tag}' matches APP_VERSION_DEFAULT '{version}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
