"""
Windows Notification Manager for Study Lock.

Provides Windows 10+ Toast notifications for focus milestones
and session events.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for Windows toast notifications."""

    def __init__(self):
        """Initialize notification manager."""
        self._try_import_wintoast()

    def _try_import_wintoast(self) -> None:
        """Attempt to import Windows notification libraries."""
        try:
            # Try using pywin32 for notifications
            import win32com.client as win32
            self.win32 = win32
            self.available = True
            logger.info("✅ Windows notifications available")
        except ImportError:
            self.available = False
            logger.debug("⚠️ Windows notifications unavailable (win32com not installed)")

    def notify_focus_started(self, duration_minutes: int, frozen: bool) -> None:
        """Notify that focus session started."""
        if not self.available:
            return

        mode = "🔒 Frozen" if frozen else "📚 Normal"
        title = "Focus Session Started"
        message = f"{mode} Mode\n{duration_minutes} minutes"

        self._show_notification(title, message, icon="📚")

    def notify_milestone(self, minutes_elapsed: int, total_minutes: int) -> None:
        """Notify of progress milestone (e.g., halfway done)."""
        if not self.available or minutes_elapsed == 0:
            return

        percentage = (minutes_elapsed / total_minutes) * 100

        if percentage == 25:
            self._show_notification("25% Complete", "You're doing great! ✨", icon="⏱️")
        elif percentage == 50:
            self._show_notification("Halfway There! 🎯", "Keep up the focus!", icon="⏱️")
        elif percentage == 75:
            self._show_notification("Almost Done! 🌟", "Final stretch!", icon="⏱️")

    def notify_break_started(self, break_minutes: int) -> None:
        """Notify that break started."""
        if not self.available:
            return

        title = "Break Time! 🌟"
        message = f"Enjoy your {break_minutes} minute break"

        self._show_notification(title, message, icon="🌟")

    def notify_session_completed(self, total_minutes: int) -> None:
        """Notify that session completed."""
        if not self.available:
            return

        hours = total_minutes // 60
        mins = total_minutes % 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

        title = "Session Complete! 🎉"
        message = f"Great work! {time_str} focused"

        self._show_notification(title, message, icon="🎉")

    def notify_distraction_blocked(self, item: str) -> None:
        """Notify that a distraction was blocked."""
        if not self.available:
            return

        title = "Distraction Blocked 🚫"
        message = f"'{item}' blocked during focus"

        self._show_notification(title, message, icon="🚫")

    def _show_notification(
        self, title: str, message: str, icon: str = "📚", duration: int = 5
    ) -> None:
        """
        Show Windows toast notification.

        Args:
            title: Notification title
            message: Notification message
            icon: Emoji or icon to display
            duration: Display duration in seconds
        """
        if not self.available:
            return

        try:
            # Use WScript.Shell for notifications (simpler, works on all Windows)
            shell = self.win32.Dispatch("WScript.Shell")
            shell.Popup(f"{icon}\n\n{title}\n\n{message}", duration, "Study Lock")
            logger.debug(f"Notification: {title}")
        except Exception as e:
            logger.debug(f"Failed to show notification: {e}")


# Global notification manager instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get or create global notification manager."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
