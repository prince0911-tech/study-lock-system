"""
Database migration system for moving from project directory to %APPDATA%.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from backend.core.paths import (
    DATABASE_PATH,
    LEGACY_DATABASE_PATH,
    MIGRATION_LOCK_PATH,
    ensure_directories,
)

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Run all pending database migrations."""
    ensure_directories()

    # Check if migrations already run
    if MIGRATION_LOCK_PATH.exists():
        logger.debug("Migrations already completed")
        return

    logger.info("Running database migrations...")

    # Migration 1: Move database from project to %APPDATA%
    _migrate_database_location()

    # Mark migrations as complete
    MIGRATION_LOCK_PATH.write_text("completed", encoding="utf-8")
    logger.info("✅ All migrations completed")


def _migrate_database_location() -> None:
    """Migrate database from project directory to %APPDATA%."""
    logger.info("📁 Migrating database location...")

    # If new location already exists, skip
    if DATABASE_PATH.exists():
        logger.info("✅ Database already in new location")
        return

    # If old location exists, copy it
    if LEGACY_DATABASE_PATH.exists():
        try:
            logger.info(f"📋 Copying database from {LEGACY_DATABASE_PATH} to {DATABASE_PATH}")
            DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LEGACY_DATABASE_PATH, DATABASE_PATH)
            logger.info("✅ Database migrated successfully")
        except Exception as e:
            logger.error(f"❌ Failed to migrate database: {e}")
            raise
    else:
        logger.info("ℹ️  No existing database to migrate")


def get_backup_path() -> Path:
    """Get path for database backup."""
    return DATABASE_PATH.parent / f"study_lock_backup.db"


def backup_database() -> bool:
    """Create backup of current database."""
    if not DATABASE_PATH.exists():
        return False

    try:
        backup_path = get_backup_path()
        shutil.copy2(DATABASE_PATH, backup_path)
        logger.info(f"✅ Database backed up to {backup_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to backup database: {e}")
        return False


def restore_database() -> bool:
    """Restore database from backup."""
    backup_path = get_backup_path()
    if not backup_path.exists():
        logger.warning("No backup found to restore")
        return False

    try:
        shutil.copy2(backup_path, DATABASE_PATH)
        logger.info("✅ Database restored from backup")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to restore database: {e}")
        return False
