#!/usr/bin/env python3
"""
Bump the app version across every file that needs to carry it in sync
(see Docs/reference/VERSIONING.md). Single command instead of a manual
find-and-replace across 3 files - the exact gap that once left the
footer stuck on an old version while /version had already moved on.

Usage:
    python scripts/bump_version.py 1.0.0-rc4
    python scripts/bump_version.py 1.0.0
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# SemVer 2.0.0 core + optional pre-release identifier. The pre-release
# identifier is required to be lowercase here (e.g. "rc4", not "RC4") -
# see Docs/reference/VERSIONING.md for why this is the one place case
# is enforced, even though the project's git tags/branches for the same
# release conventionally use uppercase ("1.0.0-RC4").
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-z0-9]+(\.[a-z0-9]+)*)?$")

# Files where the version string is mechanically replaced - each one
# holds it in a fixed, single-line, machine-parsed form. Prose docs
# (README.md, ROADMAP.md, Docs/guides/USER_GUIDE.md...) mention the
# version too but in free-form sentences a regex could corrupt or
# wrongly match a *historical* mention (e.g. "1.0.0-rc2" inside a
# changelog paragraph) - those are listed for manual review instead,
# not touched here.
REPLACEMENTS = [
    (
        "app/utils/health.py",
        re.compile(r'APP_VERSION_DEFAULT = "([^"]+)"'),
        'APP_VERSION_DEFAULT = "{new_version}"',
    ),
    (
        ".env.example",
        re.compile(r"^APP_VERSION=.+$", re.MULTILINE),
        "APP_VERSION={new_version}",
    ),
    (
        "docker/.env.example",
        re.compile(r"^APP_VERSION=.+$", re.MULTILINE),
        "APP_VERSION={new_version}",
    ),
]

# Prose docs that mention the version but aren't mechanically rewritten
# - printed as a reminder, with the exact matching lines, so nothing
# gets missed.
PROSE_DOCS = [
    "README.md",
    "ROADMAP.md",
    "Docs/guides/USER_GUIDE.md",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <new-version>", file=sys.stderr)
        return 1

    new_version = sys.argv[1]
    if not VERSION_RE.match(new_version):
        print(
            f"'{new_version}' doesn't look like a valid SemVer version "
            "(expected e.g. '1.0.0' or '1.0.0-rc4', lowercase pre-release).",
            file=sys.stderr,
        )
        return 1

    old_version = _current_version()
    if old_version is None:
        print(
            "Could not read the current APP_VERSION_DEFAULT from "
            "app/utils/health.py - aborting.",
            file=sys.stderr,
        )
        return 1

    for rel_path, pattern, template in REPLACEMENTS:
        path = ROOT / rel_path
        content = path.read_text()
        new_content, count = pattern.subn(
            template.format(new_version=new_version), content
        )
        if count == 0:
            print(f"Warning: no match found in {rel_path}, left unchanged.")
            continue
        path.write_text(new_content)
        print(f"Updated {rel_path}: {old_version} -> {new_version}")

    print()
    print(
        f"Version bumped: {old_version} -> {new_version}. Now check these "
        "prose docs for a matching update (not rewritten automatically):"
    )
    for rel_path in PROSE_DOCS:
        path = ROOT / rel_path
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if old_version in line:
                print(f"  {rel_path}:{lineno}: {line.strip()}")

    print()
    print(
        "Next steps: commit this bump, merge it, then tag the release "
        "(git tag 1.0.0-RCx or vX.Y.Z, uppercase RC by convention) and run "
        "`make check-version` to confirm the tag and APP_VERSION_DEFAULT "
        "agree - see Docs/reference/VERSIONING.md."
    )
    return 0


def _current_version() -> str | None:
    content = (ROOT / "app/utils/health.py").read_text()
    match = re.search(r'APP_VERSION_DEFAULT = "([^"]+)"', content)
    return match.group(1) if match else None


if __name__ == "__main__":
    sys.exit(main())
