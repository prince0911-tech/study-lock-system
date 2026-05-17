from __future__ import annotations

import shutil
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from backend.core.constants import (
    DEFAULT_ALLOWED_APPS,
    DEFAULT_ALLOWED_SITES,
    DEFAULT_BLOCKED_APPS,
    DEFAULT_BLOCKED_SITES,
)
from backend.core.paths import DATABASE_PATH, LEGACY_DATABASE_PATH, ensure_directories


class DatabaseManager:
    def __init__(self, db_path: Path = DATABASE_PATH) -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        ensure_directories()
        self._migrate_legacy_database()
        self.initialize()

    def _migrate_legacy_database(self) -> None:
        if self.db_path.exists() or not LEGACY_DATABASE_PATH.exists():
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY_DATABASE_PATH, self.db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    planned_minutes INTEGER NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    frozen_mode INTEGER NOT NULL DEFAULT 0,
                    strict_whitelist INTEGER NOT NULL DEFAULT 1,
                    reward_break_minutes INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS distraction_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    details TEXT,
                    action_taken TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS app_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    process_name TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    action TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    value TEXT NOT NULL UNIQUE,
                    rule_type TEXT NOT NULL,
                    action TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT
                );
                """
            )
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = (
            [(value, "app", "allow") for value in DEFAULT_ALLOWED_APPS]
            + [(value, "app", "block") for value in DEFAULT_BLOCKED_APPS]
            + [(value, "site", "allow") for value in DEFAULT_ALLOWED_SITES]
            + [(value, "site", "block") for value in DEFAULT_BLOCKED_SITES]
        )
        with self.connection() as conn:
            for value, rule_type, action in defaults:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO rules (value, rule_type, action)
                    VALUES (?, ?, ?)
                    """,
                    (value.lower(), rule_type, action),
                )
            base_settings = {
                "require_admin": False,
                "block_task_manager": True,
                "start_with_windows": True,
                "use_openai": False,
                "openai_api_key": "",
                "openai_model": "gpt-4.1-mini",
                "settings_password_hash": "",
            }
            for key, value in base_settings.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(value)),
                )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def set_setting(self, key: str, value: Any) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, json.dumps(value)),
            )

    def list_rules(self) -> dict[str, list[str]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT value, rule_type, action FROM rules").fetchall()
        grouped = {
            "allowed_apps": [],
            "blocked_apps": [],
            "allowed_sites": [],
            "blocked_sites": [],
        }
        for row in rows:
            key = f"{'allowed' if row['action'] == 'allow' else 'blocked'}_{row['rule_type']}s"
            grouped[key].append(row["value"])
        for values in grouped.values():
            values.sort()
        return grouped

    def upsert_rule(self, value: str, rule_type: str, action: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO rules (value, rule_type, action) VALUES (?, ?, ?)
                ON CONFLICT(value) DO UPDATE SET rule_type = excluded.rule_type, action = excluded.action
                """,
                (value.lower(), rule_type, action),
            )
        self.log_event("rule_updated", f"{action} {rule_type}: {value.lower()}")

    def delete_rule(self, value: str) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM rules WHERE value = ?", (value.lower(),))
        self.log_event("rule_deleted", f"Removed rule: {value.lower()}")

    def create_session(
        self,
        session_type: str,
        planned_minutes: int,
        frozen_mode: bool,
        strict_whitelist: bool,
        reward_break_minutes: int = 0,
    ) -> int:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (
                    session_type, start_time, planned_minutes, frozen_mode,
                    strict_whitelist, reward_break_minutes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_type,
                    now,
                    planned_minutes,
                    int(frozen_mode),
                    int(strict_whitelist),
                    reward_break_minutes,
                ),
            )
            session_id = int(cursor.lastrowid)
        self.log_event("session_started", f"Started {session_type} session {session_id}")
        return session_id

    def finish_session(self, session_id: int, completed: bool) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET end_time = ?, completed = ?
                WHERE id = ?
                """,
                (datetime.utcnow().isoformat(), int(completed), session_id),
            )
        self.log_event(
            "session_completed" if completed else "session_aborted",
            f"Session {session_id} completed={completed}",
        )

    def log_distraction_attempt(
        self,
        source_type: str,
        target: str,
        details: str,
        action_taken: str,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO distraction_attempts (
                    created_at, source_type, target, details, action_taken
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    source_type,
                    target,
                    details,
                    action_taken,
                ),
            )

    def log_app_usage(self, process_name: str, pid: int, action: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO app_usage_logs (created_at, process_name, pid, action)
                VALUES (?, ?, ?, ?)
                """,
                (datetime.utcnow().isoformat(), process_name.lower(), pid, action),
            )

    def log_event(self, event_type: str, message: str, payload: dict[str, Any] | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO system_events (created_at, event_type, message, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    event_type,
                    message,
                    json.dumps(payload or {}),
                ),
            )

    def get_dashboard_stats(self) -> dict[str, Any]:
        now = datetime.utcnow()
        today = now.date().isoformat()
        week_start = (now - timedelta(days=6)).date().isoformat()
        with self.connection() as conn:
            daily_minutes = conn.execute(
                """
                SELECT COALESCE(SUM(planned_minutes), 0) AS minutes
                FROM sessions
                WHERE completed = 1
                AND date(start_time) = date(?)
                AND session_type = 'focus'
                """,
                (today,),
            ).fetchone()["minutes"]
            weekly_minutes = conn.execute(
                """
                SELECT COALESCE(SUM(planned_minutes), 0) AS minutes
                FROM sessions
                WHERE completed = 1
                AND date(start_time) >= date(?)
                AND session_type = 'focus'
                """,
                (week_start,),
            ).fetchone()["minutes"]
            attempts_today = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM distraction_attempts
                WHERE date(created_at) = date(?)
                """,
                (today,),
            ).fetchone()["count"]
            sessions_completed = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM sessions
                WHERE completed = 1
                AND date(start_time) = date(?)
                AND session_type = 'focus'
                """,
                (today,),
            ).fetchone()["count"]
            recent_events = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT created_at, event_type, message
                    FROM system_events
                    ORDER BY id DESC
                    LIMIT 20
                    """
                ).fetchall()
            ]
        return {
            "daily_minutes": int(daily_minutes or 0),
            "weekly_minutes": int(weekly_minutes or 0),
            "streak_days": self._calculate_streak(),
            "distraction_attempts_today": int(attempts_today or 0),
            "sessions_completed_today": int(sessions_completed or 0),
            "recent_events": recent_events,
        }

    def _calculate_streak(self) -> int:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT date(start_time) AS d
                FROM sessions
                WHERE completed = 1 AND session_type = 'focus'
                ORDER BY d DESC
                """
            ).fetchall()
        dates = {row["d"] for row in rows}
        streak = 0
        cursor = datetime.utcnow().date()
        while cursor.isoformat() in dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak
