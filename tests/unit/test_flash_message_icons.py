"""
Regression test: flash() messages must never contain an emoji.

base.html's flash block already prepends a Font Awesome icon based on
the flash category (success/danger/warning/info) - a message text that
also starts with an emoji (✅/❌/⚠️/etc.) renders two icons side by side.
Font Awesome is this project's only icon convention; emoji are never
used alongside or instead of it (see CLAUDE.md's Frontend section).

Scans source rather than rendering routes: cheaper, and catches the bug
at the only place it can be introduced (a flash() call embedding an
emoji), regardless of which route/branch would exercise it.

app/utils/automation/ is deliberately excluded: those modules encode a
generated message's severity as a leading emoji, consumed and stripped
by app/routes/admin_automation_routes.py's _classify_automation_message()
before ever reaching flash() or a template - the emoji there is
compile-time-invisible to the pattern below anyway (never inside a
flash() call), so no special-casing is needed for this test's method,
but the reasoning is worth keeping visible so nobody "fixes" the emoji
in that file by analogy with this test.
"""

import ast
import re
from pathlib import Path

# Any character in the common emoji ranges (misc symbols, dingbats,
# transport/map symbols, supplemental symbols and pictographs, plus the
# variation-selector-16 that often trails "text-style" emoji like ⚠️).
_EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿️]")

ROUTE_DIRS = [
    Path(__file__).parent.parent.parent / "app" / "routes",
    Path(__file__).parent.parent.parent / "app" / "auth",
]


def _iter_flash_call_string_args():
    """Yield (file, lineno, string_value) for every literal/f-string/
    gettext-wrapped argument passed as the first positional argument to
    a flash() call, across app/routes/ and app/auth/."""
    for directory in ROUTE_DIRS:
        for path in sorted(directory.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "flash"
                    and node.args
                ):
                    first_arg = node.args[0]
                    # gettext-wrapped: flash(_("...", ...))
                    if (
                        isinstance(first_arg, ast.Call)
                        and isinstance(first_arg.func, ast.Name)
                        and first_arg.func.id == "_"
                        and first_arg.args
                    ):
                        first_arg = first_arg.args[0]
                    # Constant string: flash("...")
                    if isinstance(first_arg, ast.Constant) and isinstance(
                        first_arg.value, str
                    ):
                        yield path, first_arg.lineno, first_arg.value
                    # f-string: flash(f"...")
                    elif isinstance(first_arg, ast.JoinedStr):
                        literal_parts = "".join(
                            v.value
                            for v in first_arg.values
                            if isinstance(v, ast.Constant)
                        )
                        yield path, first_arg.lineno, literal_parts


class TestFlashMessagesHaveNoEmoji:
    def test_no_flash_call_contains_an_emoji(self):
        offenders = [
            f"{path.relative_to(Path(__file__).parent.parent.parent)}:{lineno}: {value!r}"
            for path, lineno, value in _iter_flash_call_string_args()
            if _EMOJI_RE.search(value)
        ]
        assert offenders == [], (
            "flash() message(s) contain an emoji - base.html's flash block "
            "already renders a Font Awesome icon per category, so an emoji "
            "in the text produces a double icon:\n" + "\n".join(offenders)
        )

    def test_scan_actually_finds_flash_calls(self):
        """Guards the test above against a silent false-negative (e.g. a
        refactor renaming flash imports so the AST walk matches
        nothing)."""
        assert len(list(_iter_flash_call_string_args())) > 50
