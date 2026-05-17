from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
import winreg
from pathlib import Path

import psutil

from backend.core.constants import API_PORT, APP_NAME, ESSENTIAL_PROCESS_NAMES

logger = logging.getLogger(__name__)

HOSTS_FILE_PATH = Path(r"C:\Windows\System32\drivers\etc\hosts")
HOSTS_BLOCK_START = "# >>> Study Lock System blocked sites >>>"
HOSTS_BLOCK_END = "# <<< Study Lock System blocked sites <<<"


class WindowsControl:
    def is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def relaunch_as_admin(self) -> None:
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1,
        )

    def list_processes(self) -> list[psutil.Process]:
        return list(psutil.process_iter(["pid", "ppid", "name", "exe", "username"]))

    def kill_process(self, proc: psutil.Process) -> bool:
        try:
            proc.terminate()
            proc.wait(timeout=2)
            return True
        except Exception:
            try:
                proc.kill()
                return True
            except Exception:
                return False

    def register_startup(self, command: str) -> None:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
            finally:
                winreg.CloseKey(key)
        except OSError as exc:
            logger.warning("Unable to register startup entry: %s", exc)

    def unregister_startup(self) -> None:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            finally:
                winreg.CloseKey(key)
        except OSError as exc:
            logger.warning("Unable to remove startup entry: %s", exc)

    def is_essential_process(self, process_name: str) -> bool:
        return process_name.lower() in ESSENTIAL_PROCESS_NAMES

    def ensure_firewall_open(self) -> None:
        command = [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={APP_NAME} Local API {API_PORT}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={API_PORT}",
        ]
        try:
            subprocess.run(command, check=False, capture_output=True, text=True)
        except Exception as exc:
            logger.warning("Firewall rule setup skipped: %s", exc)

    def apply_site_blocks(self, domains: tuple[str, ...]) -> bool:
        entries: list[str] = []
        for domain in domains:
            normalized = domain.strip().lower()
            if not normalized:
                continue
            entries.append(f"127.0.0.1 {normalized}")
            if not normalized.startswith("www."):
                entries.append(f"127.0.0.1 www.{normalized}")
        return self._write_hosts_block(entries)

    def clear_site_blocks(self) -> bool:
        return self._write_hosts_block([])

    def _write_hosts_block(self, entries: list[str]) -> bool:
        try:
            existing = HOSTS_FILE_PATH.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            existing = HOSTS_FILE_PATH.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("Unable to read hosts file: %s", exc)
            return False

        managed_block = ""
        if entries:
            managed_block = "\n".join(
                [HOSTS_BLOCK_START, *entries, HOSTS_BLOCK_END]
            )
        updated = self._replace_managed_hosts_block(existing, managed_block)
        if updated == existing:
            return True

        try:
            HOSTS_FILE_PATH.write_text(updated, encoding="utf-8")
            return True
        except OSError as exc:
            logger.warning("Unable to update hosts file. Run as administrator to block sites in all browsers: %s", exc)
            return False

    @staticmethod
    def _replace_managed_hosts_block(existing: str, managed_block: str) -> str:
        start = existing.find(HOSTS_BLOCK_START)
        end = existing.find(HOSTS_BLOCK_END)
        base = existing
        if start != -1 and end != -1 and end >= start:
            end += len(HOSTS_BLOCK_END)
            if end < len(existing) and existing[end:end + 1] == "\n":
                end += 1
            base = existing[:start].rstrip() + "\n"
            remainder = existing[end:].lstrip("\n")
            if remainder:
                base += remainder
        if not managed_block:
            return base.rstrip() + "\n"
        base = base.rstrip()
        if base:
            return f"{base}\n\n{managed_block}\n"
        return f"{managed_block}\n"
