"""Remplit mécaniquement les msgstr vides/fuzzy de fr.po avec le msgid.

fr.po est la source française elle-même (msgid == texte affiché), donc ce
remplissage n'est jamais une traduction à écrire à la main - contrairement à
en.po. `pybabel update` ne copie jamais msgid dans msgstr automatiquement, et
peut marquer une entrée "fuzzy" (mauvais rapprochement) sur une nouvelle
chaîne courte ; ce script corrige les deux cas pour fr uniquement.

Appelé par `make babel-update`, jamais par `make babel-compile` (qui ne doit
pas modifier les .po).
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
