from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = PROJECT_ROOT / "runtime"
LOG_DIR = PROJECT_ROOT / "logs"
DATABASE_DIR = PROJECT_ROOT / "database"
ASSETS_DIR = PROJECT_ROOT / "assets"
EXTENSION_DIR = PROJECT_ROOT / "extension"
DOCS_DIR = PROJECT_ROOT / "docs"
INSTALLER_DIR = PROJECT_ROOT / "installer"

APP_DATA_DIR = RUNTIME_ROOT / "data"
CONFIG_DIR = RUNTIME_ROOT / "config"
STATE_DIR = RUNTIME_ROOT / "state"

LEGACY_DATABASE_PATH = DATABASE_DIR / "study_lock.db"
DATABASE_PATH = APP_DATA_DIR / "study_lock.db"
SETTINGS_PATH = CONFIG_DIR / "settings.enc"
SECRET_KEY_PATH = CONFIG_DIR / "fernet.key"
RUNTIME_STATE_PATH = STATE_DIR / "runtime_state.json"
WATCHDOG_LOCK_PATH = STATE_DIR / "watchdog.lock"


def ensure_directories() -> None:
    for path in (
        RUNTIME_ROOT,
        LOG_DIR,
        DATABASE_DIR,
        APP_DATA_DIR,
        CONFIG_DIR,
        STATE_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
