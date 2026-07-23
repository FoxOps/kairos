"""Mechanically fills fr.po's empty/fuzzy msgstr with the msgid.

fr.po is the French source itself (msgid == displayed text), so this
fill is never a translation that needs writing by hand - unlike en.po.
`pybabel update` never automatically copies msgid into msgstr, and can
mark an entry "fuzzy" (bad match) on a new short string; this script
fixes both cases for fr only.

Called by `make babel-update`, never by `make babel-compile` (which must
not modify the .po files).
"""

import sys
from pathlib import Path

import polib

FR_CATALOG = (
    Path(__file__).resolve().parent.parent
    / "app/translations/fr/LC_MESSAGES/messages.po"
)


def fill_fr_catalog(path: Path) -> int:
    po = polib.pofile(str(path))
    filled = 0
    for entry in po:
        if entry.obsolete:
            continue
        if not entry.msgstr or entry.fuzzy:
            entry.msgstr = entry.msgid
            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
            filled += 1
    if filled:
        po.save(str(path))
    return filled


if __name__ == "__main__":
    count = fill_fr_catalog(FR_CATALOG)
    print(f"fr.po: {count} entrée(s) remplie(s)/corrigée(s)")
    sys.exit(0)
