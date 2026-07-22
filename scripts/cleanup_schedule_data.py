#!/usr/bin/env python3
"""
Kairos - Purge des shifts/astreintes anciens
=============================================

Supprime les shifts et astreintes passés depuis plus longtemps que la
durée de rétention configurée (Setting "schedule_retention_days",
/admin/settings, 365 jours par défaut, 0 = ne jamais purger) - évite
d'accumuler des années de données de planning sans usage réel dans la
base.

À exécuter chaque jour via cron - voir docker/crontabs/appuser. No-op
silencieux si schedule_retention_days vaut 0.

Utilisation:
    python scripts/cleanup_schedule_data.py
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from app.services import ScheduleCleanupService  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> int:
    with app.app_context():
        result = ScheduleCleanupService.purge_old_data()

    if result.skipped:
        logger.info("Purge désactivée (schedule_retention_days=0) - rien à faire.")
        return 0

    logger.info(
        "Purge effectuée (rétention %d jours) : %d shift(s), %d astreinte(s) supprimé(s).",
        result.retention_days,
        result.shifts_deleted,
        result.oncalls_deleted,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
