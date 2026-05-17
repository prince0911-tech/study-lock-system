from __future__ import annotations

import logging
import os
import threading
import time

import psutil

from backend.core.constants import BROWSER_PROCESS_NAMES
from backend.services.database import DatabaseManager
from backend.services.policy import PolicyManager
from backend.services.session_manager import SessionManager
from backend.services.windows_control import WindowsControl

logger = logging.getLogger(__name__)


class ProcessMonitor:
    def __init__(
        self,
        db: DatabaseManager,
        policy: PolicyManager,
        sessions: SessionManager,
        windows: WindowsControl,
    ) -> None:
        self.db = db
        self.policy = policy
        self.sessions = sessions
        self.windows = windows
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._running = False
        self._applied_blocked_sites: tuple[str, ...] = ()
        self._site_blocks_initialized = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread.start()

    def _loop(self) -> None:
        while True:
            try:
                self._enforce()
            except Exception as exc:
                logger.exception("Process monitor error: %s", exc)
                self.db.log_event("process_monitor_error", "Process monitor crashed", {"error": str(exc)})
            time.sleep(2)

    def _enforce(self) -> None:
        state = self.sessions.get_state()
        if not state.is_active or state.is_break:
            self._sync_site_blocks(())
            return

        rules = self.policy.load_rules()
        self._sync_site_blocks(tuple(rules["blocked_sites"]))
        allowed_apps = set(rules["allowed_apps"])
        blocked_apps = set(rules["blocked_apps"])
        protected_pids = {os.getpid(), os.getppid()}
        if not self.db.get_setting("block_task_manager", True):
            blocked_apps.discard("taskmgr.exe")

        for proc in self.windows.list_processes():
            try:
                name = (proc.info.get("name") or "").lower()
                pid = int(proc.info["pid"])
                ppid = int(proc.info.get("ppid") or 0)
                if not name or pid == 0 or self.windows.is_essential_process(name):
                    continue
                if pid in protected_pids or ppid == os.getpid():
                    continue
                if name in BROWSER_PROCESS_NAMES:
                    continue
                if name in blocked_apps:
                    if self.windows.kill_process(proc):
                        self.db.log_app_usage(name, pid, "terminated_block_rule")
                        self.db.log_distraction_attempt("app", name, "Blocked app rule", "terminated")
                    continue
                if state.strict_whitelist and name not in allowed_apps:
                    username = (proc.info.get("username") or "").lower()
                    if "system" in username or "local service" in username or "network service" in username:
                        continue
                    if self.windows.kill_process(proc):
                        self.db.log_app_usage(name, pid, "terminated_not_whitelisted")
                        self.db.log_distraction_attempt("app", name, "Strict whitelist enforcement", "terminated")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def _sync_site_blocks(self, blocked_sites: tuple[str, ...]) -> None:
        normalized = tuple(sorted({site.lower() for site in blocked_sites if site.strip()}))
        if self._site_blocks_initialized and normalized == self._applied_blocked_sites:
            return
        if normalized:
            if self.windows.apply_site_blocks(normalized):
                self._applied_blocked_sites = normalized
            self._site_blocks_initialized = True
        else:
            self.windows.clear_site_blocks()
            self._applied_blocked_sites = ()
            self._site_blocks_initialized = True
