"""
Automated SQLite database backup.

Creates timestamped copies of all .db files in instance/ to instance/backups/.
Auto-prunes backups older than 7 days.

Usage:
    Standalone:  python scripts/daily_imports/backup_database.py
    From code:   from scripts.daily_imports.backup_database import run_backup
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
INSTANCE_DIR = BASE_DIR / "instance"
BACKUP_DIR = INSTANCE_DIR / "backups"
RETENTION_DAYS = 7


def run_backup(
    instance_dir: Path = INSTANCE_DIR,
    backup_dir: Path = BACKUP_DIR,
    retention_days: int = RETENTION_DAYS,
) -> Path | None:
    """
    Back up all .db files in *instance_dir* to a timestamped subfolder
    inside *backup_dir*.  Returns the backup folder path, or None if
    there were no databases to back up.
    """
    instance_dir = Path(instance_dir)
    backup_dir = Path(backup_dir)

    db_files = list(instance_dir.glob("*.db"))
    if not db_files:
        logger.info("No .db files found in %s — nothing to back up.", instance_dir)
        return None

    # Create timestamped subfolder: instance/backups/2026-03-07_15-30/
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dest = backup_dir / timestamp
    dest.mkdir(parents=True, exist_ok=True)

    for db_file in db_files:
        target = dest / db_file.name
        shutil.copy2(db_file, target)
        size_mb = target.stat().st_size / (1024 * 1024)
        logger.info("Backed up %s → %s (%.1f MB)", db_file.name, target, size_mb)

    # ── Prune old backups ─────────────────────────────────────────────
    _prune_old_backups(backup_dir, retention_days)

    return dest


def _prune_old_backups(backup_dir: Path, retention_days: int) -> None:
    """Remove backup subdirectories older than *retention_days*."""
    if not backup_dir.exists():
        return

    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0

    for entry in sorted(backup_dir.iterdir()):
        if not entry.is_dir():
            continue
        try:
            # Parse the folder name back to a datetime
            folder_dt = datetime.strptime(entry.name, "%Y-%m-%d_%H-%M")
        except ValueError:
            continue  # skip folders that don't match the pattern

        if folder_dt < cutoff:
            shutil.rmtree(entry)
            removed += 1
            logger.info("Pruned old backup: %s", entry.name)

    if removed:
        logger.info("Pruned %d backup(s) older than %d days.", removed, retention_days)


# ── CLI entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    result = run_backup()
    if result:
        print(f"Backup complete → {result}")
    else:
        print("No databases found to back up.")
