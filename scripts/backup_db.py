from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path("/opt/clinic-income-bot")
DATABASE_PATH = PROJECT_DIR / "clinic_income.db"
BACKUP_DIR = PROJECT_DIR / "backups"
MAX_BACKUPS = 30


def create_backup() -> Path:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(BACKUP_DIR, 0o700)

    timestamp = datetime.now().astimezone().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    final_path = BACKUP_DIR / f"clinic_income_{timestamp}.db"
    temporary_path = BACKUP_DIR / f".{final_path.name}.tmp"

    try:
        with sqlite3.connect(
            DATABASE_PATH,
            timeout=30,
        ) as source_database:
            with sqlite3.connect(temporary_path) as backup_database:
                source_database.backup(backup_database)

                integrity_result = backup_database.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                if (
                    integrity_result is None
                    or integrity_result[0] != "ok"
                ):
                    raise RuntimeError(
                        "Backup integrity check failed."
                    )

        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, final_path)

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    remove_old_backups()

    return final_path


def remove_old_backups() -> None:
    backups = sorted(
        BACKUP_DIR.glob("clinic_income_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[MAX_BACKUPS:]:
        old_backup.unlink(missing_ok=True)


if __name__ == "__main__":
    created_backup = create_backup()
    print(created_backup)
