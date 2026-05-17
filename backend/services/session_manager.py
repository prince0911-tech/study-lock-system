from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from backend.core.paths import RUNTIME_STATE_PATH
from backend.services.database import DatabaseManager


@dataclass
class SessionState:
    is_active: bool = False
    is_break: bool = False
    frozen_mode: bool = False
    strict_whitelist: bool = True
    end_time: str | None = None
    seconds_remaining: int = 0
    session_id: int | None = None
    reward_break_minutes: int = 0


class SessionManager:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self.state = SessionState()
        self._lock = threading.RLock()
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()

    def start_focus(self, duration_minutes: int, break_minutes: int, frozen_mode: bool, strict_whitelist: bool) -> SessionState:
        with self._lock:
            if self.state.is_active:
                return self.state
            session_id = self.db.create_session(
                session_type="focus",
                planned_minutes=duration_minutes,
                frozen_mode=frozen_mode,
                strict_whitelist=strict_whitelist,
                reward_break_minutes=break_minutes,
            )
            end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
            self.state = SessionState(
                is_active=True,
                is_break=False,
                frozen_mode=frozen_mode,
                strict_whitelist=strict_whitelist,
                end_time=end_time.isoformat(),
                seconds_remaining=duration_minutes * 60,
                session_id=session_id,
                reward_break_minutes=break_minutes,
            )
            self._write_runtime_state()
            return self.state

    def stop_focus(self, allow_abort: bool) -> SessionState:
        with self._lock:
            if not self.state.is_active:
                return self.state
            if self.state.frozen_mode and not allow_abort and not self.state.is_break:
                return self.state
            session_id = self.state.session_id
            was_break = self.state.is_break
            self.db.finish_session(session_id, completed=was_break)
            self.state = SessionState()
            self._write_runtime_state()
            return self.state

    def get_state(self) -> SessionState:
        with self._lock:
            return self.state

    def _tick_loop(self) -> None:
        while True:
            with self._lock:
                if self.state.is_active and self.state.end_time:
                    delta = int(
                        (datetime.fromisoformat(self.state.end_time) - datetime.utcnow()).total_seconds()
                    )
                    self.state.seconds_remaining = max(0, delta)
                    if delta <= 0:
                        self._advance_session()
                    self._write_runtime_state()
            time.sleep(1)

    def _advance_session(self) -> None:
        if not self.state.is_break:
            session_id = self.state.session_id
            self.db.finish_session(session_id, completed=True)
            break_id = self.db.create_session(
                session_type="break",
                planned_minutes=self.state.reward_break_minutes,
                frozen_mode=False,
                strict_whitelist=False,
            )
            end_time = datetime.utcnow() + timedelta(minutes=self.state.reward_break_minutes)
            self.state = SessionState(
                is_active=True,
                is_break=True,
                frozen_mode=False,
                strict_whitelist=False,
                end_time=end_time.isoformat(),
                seconds_remaining=self.state.reward_break_minutes * 60,
                session_id=break_id,
                reward_break_minutes=0,
            )
        else:
            self.db.finish_session(self.state.session_id, completed=True)
            self.state = SessionState()

    def _write_runtime_state(self) -> None:
        payload = asdict(self.state)
        RUNTIME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
