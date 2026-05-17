from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from backend.core.paths import RUNTIME_STATE_PATH, WATCHDOG_LOCK_PATH


def run_watchdog(target_script: Path) -> None:
    WATCHDOG_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHDOG_LOCK_PATH.write_text(str(time.time()), encoding="utf-8")
    while True:
        state = _read_state()
        if state.get("is_active") and not _is_running("study_lock_gui.py"):
            subprocess.Popen([sys.executable, str(target_script)], creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(5)


def _read_state() -> dict:
    if not RUNTIME_STATE_PATH.exists():
        return {}
    try:
        return json.loads(RUNTIME_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_running(marker: str) -> bool:
    import psutil

    for proc in psutil.process_iter(["cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if marker.lower() in cmdline.lower():
                return True
        except Exception:
            continue
    return False
