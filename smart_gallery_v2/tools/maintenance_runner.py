"""Maintenance runner: cleans orphaned DB rows and broken symlinks.

Run this script from the repository root or via the scheduled-task PowerShell helper.

Improvements: supports `--dry-run` to preview removals and `--log-file` for persistent rotative logs.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.database import DatabaseManager
from core.metrics import metrics


def setup_logging(log_file: str | None) -> None:
    fmt = "%(asctime)s %(levelname)s %(message)s"
    if log_file:
        handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(fmt))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(handler)
    else:
        logging.basicConfig(level=logging.INFO, format=fmt)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smart Gallery maintenance runner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't delete rows; just report what would be removed",
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="Skip database backup before cleanup"
    )
    parser.add_argument("--limit", type=int, default=1000, help="Max rows to process per operation")
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Optional log file path with rotation",
    )
    args = parser.parse_args(argv)

    setup_logging(args.log_file)
    log = logging.getLogger("maintenance_runner")

    db = DatabaseManager()
    try:
        start_time = datetime.now()
        log.info("Maintenance run (dry_run=%s, limit=%d)", args.dry_run, args.limit)

        # Backup database before cleanup (unless --no-backup)
        if not args.no_backup and not args.dry_run:
            try:
                db_path = Path(ROOT) / "db" / "smart_gallery.db"
                if db_path.exists():
                    backup_dir = db_path.parent / "backups"
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = backup_dir / f"smart_gallery_backup_{timestamp}.db"
                    shutil.copy2(db_path, backup_path)
                    log.info("Database backed up to %s", backup_path)
            except Exception:
                log.exception("Database backup failed; proceeding with cleanup")

        log.info("Checking missing files...")
        missing = db.get_missing_filequeue_records(limit=args.limit)
        log.info("Found %d missing file records", len(missing))
        if not args.dry_run:
            removed_files = db.cleanup_missing_files(limit=args.limit)
            log.info("Removed %d orphaned FileQueue rows", removed_files)
        else:
            removed_files = 0

        log.info("Checking broken symlinks...")
        broken = db.get_broken_symlink_records(limit=args.limit)
        log.info("Found %d broken symlink records", len(broken))
        if not args.dry_run:
            removed_links = db.cleanup_broken_symlinks(limit=args.limit)
            log.info("Removed %d broken FileIdentity rows", removed_links)
        else:
            removed_links = 0

        # Record metrics
        elapsed = (datetime.now() - start_time).total_seconds()
        metrics.record_cleanup(removed_files, removed_links, elapsed)

        log.info("Maintenance completed in %.2f seconds", elapsed)
        return 0
    except Exception:
        log.exception("Maintenance runner failed")
        metrics.record_maintenance_error()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
