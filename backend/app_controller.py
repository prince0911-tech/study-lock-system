from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from backend.core.logging_config import configure_logging
from backend.core.paths import SETTINGS_PATH, ensure_directories
from backend.core.security import decrypt_json, encrypt_json, hash_password, verify_password
from backend.models.schemas import BrowserEvaluationResponse
from backend.services.classifier import StudyClassifier
from backend.services.database import DatabaseManager
from backend.services.policy import PolicyManager
from backend.services.process_monitor import ProcessMonitor
from backend.services.session_manager import SessionManager
from backend.services.windows_control import WindowsControl

logger = logging.getLogger(__name__)


class AppController:
    def __init__(self) -> None:
        ensure_directories()
        configure_logging()
        self.db = DatabaseManager()
        self.policy = PolicyManager(self.db)
        self.windows = WindowsControl()
        self.sessions = SessionManager(self.db)
        self.classifier = StudyClassifier(self.db, self.policy)
        self.process_monitor = ProcessMonitor(self.db, self.policy, self.sessions, self.windows)
        self.process_monitor.start()
        self._bootstrap_settings_file()
        self._apply_startup_setting()

    def _bootstrap_settings_file(self) -> None:
        settings = self.get_settings()
        encrypt_json(settings, SETTINGS_PATH)

    def _apply_startup_setting(self) -> None:
        if self.db.get_setting("start_with_windows", True):
            if getattr(sys, "frozen", False):
                command = f'"{Path(sys.executable)}"'
            else:
                command = f'"{Path(sys.executable)}" -m desktop_app.main'
            self.windows.register_startup(command)

    def evaluate_browser_content(self, url: str, title: str, page_text: str) -> BrowserEvaluationResponse:
        state = self.sessions.get_state()
        if not state.is_active or state.is_break:
            return BrowserEvaluationResponse(
                decision="ALLOW",
                category="STUDY",
                reason="Focus mode is inactive",
                confidence=1.0,
            )
        result = self.classifier.classify(url, title, page_text)
        decision = "ALLOW" if result["category"] == "STUDY" else "BLOCK"
        if decision == "BLOCK":
            self.db.log_distraction_attempt(
                "site",
                url,
                f"{title} | {result['reason']}",
                "blocked",
            )
        return BrowserEvaluationResponse(
            decision=decision,
            category=result["category"],
            reason=result["reason"],
            matched_rule=result.get("matched_rule"),
            confidence=float(result["confidence"]),
        )

    def start_focus(self, duration_minutes: int, break_minutes: int, frozen_mode: bool, strict_whitelist: bool):
        return self.sessions.start_focus(duration_minutes, break_minutes, frozen_mode, strict_whitelist)

    def stop_focus(self, force: bool = False):
        state = self.sessions.get_state()
        return self.sessions.stop_focus(allow_abort=force or not state.frozen_mode)

    def get_rules(self) -> dict[str, list[str]]:
        return self.policy.load_rules()

    def add_rule(self, value: str, rule_type: str, action: str) -> None:
        self.db.upsert_rule(value, rule_type, action)

    def delete_rule(self, value: str) -> None:
        self.db.delete_rule(value)

    def get_stats(self) -> dict:
        return self.db.get_dashboard_stats()

    def get_session_state(self):
        return self.sessions.get_state()

    def get_settings(self) -> dict:
        return {
            "require_admin": self.db.get_setting("require_admin", False),
            "block_task_manager": self.db.get_setting("block_task_manager", True),
            "start_with_windows": self.db.get_setting("start_with_windows", True),
            "use_openai": self.db.get_setting("use_openai", False),
            "openai_api_key": self.db.get_setting("openai_api_key", ""),
            "openai_model": self.db.get_setting("openai_model", "gpt-4.1-mini"),
        }

    def update_settings(self, payload: dict) -> None:
        for key, value in payload.items():
            self.db.set_setting(key, value)
        encrypt_json(self.get_settings(), SETTINGS_PATH)
        if payload.get("start_with_windows", True):
            self._apply_startup_setting()
        else:
            self.windows.unregister_startup()

    def set_password(self, current_password: str, new_password: str) -> tuple[bool, str]:
        current_hash = self.db.get_setting("settings_password_hash", "")
        if current_hash and not verify_password(current_password, current_hash):
            return False, "Current password is incorrect."
        self.db.set_setting("settings_password_hash", hash_password(new_password))
        return True, "Settings password updated."

    def verify_settings_password(self, password: str) -> bool:
        password_hash = self.db.get_setting("settings_password_hash", "")
        if not password_hash:
            return True
        return verify_password(password, password_hash)

    def load_encrypted_settings_snapshot(self) -> dict:
        return decrypt_json(SETTINGS_PATH)

    def spawn_watchdog(self, target_script: Path) -> None:
        if os.environ.get("STUDY_LOCK_WATCHDOG") == "1":
            return
        try:
            env = os.environ.copy()
            env["STUDY_LOCK_WATCHDOG"] = "1"
            subprocess.Popen(
                [sys.executable, "-m", "backend.watchdog_runner", str(target_script)],
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as exc:
            logger.warning("Watchdog launch failed: %s", exc)
