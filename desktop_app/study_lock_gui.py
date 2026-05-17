from __future__ import annotations

import logging
import threading
from datetime import timedelta
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from backend.app_controller import AppController


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title: str, accent: str) -> None:
        super().__init__(master, fg_color="#151922", corner_radius=18)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text=title,
            text_color="#94a3b8",
            font=ctk.CTkFont(size=14),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.value_label = ctk.CTkLabel(
            self,
            text="0",
            text_color=accent,
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        self.value_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

    def set_value(self, value: str) -> None:
        self.value_label.configure(text=value)


class StudyLockApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.controller = AppController()
        self.title("Study Lock System")
        self.geometry("1340x860")
        self.minsize(1120, 760)
        self.configure(fg_color="#090b10")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._start_api_server()
        self.controller.spawn_watchdog(Path(__file__).resolve())

        self.duration_var = ctk.IntVar(value=90)
        self.break_var = ctk.IntVar(value=15)
        self.frozen_var = ctk.BooleanVar(value=True)
        self.strict_var = ctk.BooleanVar(value=True)
        self.rule_type_var = ctk.StringVar(value="site")
        self.rule_action_var = ctk.StringVar(value="block")

        self._build_layout()
        self.refresh_ui()

    def _start_api_server(self) -> None:
        """Start the API server with verification and error handling."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from backend.api.server import start_api_server
            
            logger.info("Starting Flask API server...")
            success = start_api_server(self.controller, timeout=10)
            
            if not success:
                logger.error("API Server failed to start - UI will continue but API won't respond")
                messagebox.showwarning(
                    "API Server Warning",
                    "The backend API server failed to start.\n\n"
                    "The UI will work, but browser extension communication will be unavailable.\n\n"
                    "Check logs for details."
                )
            else:
                logger.info("API Server started successfully!")
                
        except Exception as e:
            logger.error(f"Error starting API server: {e}", exc_info=True)
            messagebox.showerror(
                "API Server Error",
                f"Failed to start API server:\n{e}\n\n"
                "Check logs for details."
            )

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        nav = ctk.CTkFrame(shell, width=250, fg_color="#10141d", corner_radius=24)
        nav.grid(row=0, column=0, sticky="nsw", padx=(0, 20))
        nav.grid_propagate(False)

        ctk.CTkLabel(
            nav,
            text="Study Lock",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#f8fafc",
        ).pack(anchor="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(
            nav,
            text="Windows focus enforcement",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=24, pady=(0, 24))

        control_box = ctk.CTkFrame(nav, fg_color="#161d29", corner_radius=18)
        control_box.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkLabel(control_box, text="Focus Minutes", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=14, pady=(14, 6))
        ctk.CTkEntry(control_box, textvariable=self.duration_var).pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkLabel(control_box, text="Reward Break Minutes", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=14, pady=(6, 6))
        ctk.CTkEntry(control_box, textvariable=self.break_var).pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkCheckBox(control_box, text="Frozen mode", variable=self.frozen_var).pack(anchor="w", padx=14, pady=6)
        ctk.CTkCheckBox(control_box, text="Strict whitelist", variable=self.strict_var).pack(anchor="w", padx=14, pady=(0, 10))
        ctk.CTkButton(control_box, text="Start Focus", height=42, fg_color="#2563eb", hover_color="#1d4ed8", command=self.start_focus).pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkButton(control_box, text="Emergency Stop", height=42, fg_color="#b91c1c", hover_color="#991b1b", command=self.stop_focus).pack(fill="x", padx=14, pady=(0, 14))

        self.timer_label = ctk.CTkLabel(
            nav,
            text="00:00:00",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#38bdf8",
        )
        self.timer_label.pack(anchor="w", padx=24, pady=(0, 4))
        self.status_label = ctk.CTkLabel(
            nav,
            text="Idle",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=13),
        )
        self.status_label.pack(anchor="w", padx=24, pady=(0, 24))

        content = ctk.CTkScrollableFrame(
            shell,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#334155",
            scrollbar_button_hover_color="#475569",
        )
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Dashboard",
            font=ctk.CTkFont(size=34, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Live focus telemetry, blocking rules, and session analytics",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=14),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        metrics = ctk.CTkFrame(content, fg_color="transparent")
        metrics.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        for i in range(4):
            metrics.grid_columnconfigure(i, weight=1)
        self.daily_card = StatCard(metrics, "Today", "#22c55e")
        self.weekly_card = StatCard(metrics, "This Week", "#38bdf8")
        self.streak_card = StatCard(metrics, "Streak", "#f59e0b")
        self.attempts_card = StatCard(metrics, "Blocked Attempts", "#ef4444")
        self.daily_card.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.weekly_card.grid(row=0, column=1, sticky="ew", padx=12)
        self.streak_card.grid(row=0, column=2, sticky="ew", padx=12)
        self.attempts_card.grid(row=0, column=3, sticky="ew", padx=(12, 0))

        lower = ctk.CTkFrame(content, fg_color="transparent")
        lower.grid(row=2, column=0, sticky="nsew")
        lower.grid_columnconfigure(0, weight=1)
        lower.grid_columnconfigure(1, weight=1)

        activity = ctk.CTkFrame(lower, fg_color="#10141d", corner_radius=24, height=320)
        activity.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        activity.grid_rowconfigure(1, weight=1)
        activity.grid_columnconfigure(0, weight=1)
        activity.grid_propagate(False)
        ctk.CTkLabel(activity, text="System Events", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 12))
        self.activity_box = ctk.CTkTextbox(activity, fg_color="#141b27", border_width=0)
        self.activity_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        rules = ctk.CTkFrame(lower, fg_color="#10141d", corner_radius=24, height=320)
        rules.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        rules.grid_columnconfigure(0, weight=1)
        rules.grid_propagate(False)
        ctk.CTkLabel(rules, text="Rule Manager", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        form = ctk.CTkFrame(rules, fg_color="#161d29", corner_radius=16)
        form.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.rule_value_entry = ctk.CTkEntry(form, placeholder_text="e.g. reddit.com or discord.exe")
        self.rule_value_entry.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        form.grid_columnconfigure(0, weight=1)
        ctk.CTkOptionMenu(form, values=["site", "app"], variable=self.rule_type_var).grid(row=0, column=1, padx=6, pady=12)
        ctk.CTkOptionMenu(form, values=["block", "allow"], variable=self.rule_action_var).grid(row=0, column=2, padx=6, pady=12)
        ctk.CTkButton(form, text="Add Rule", command=self.add_rule).grid(row=0, column=3, padx=12, pady=12)
        self.rules_box = ctk.CTkTextbox(rules, fg_color="#141b27", border_width=0)
        self.rules_box.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        rules.grid_rowconfigure(2, weight=1)

        settings = ctk.CTkFrame(lower, fg_color="#10141d", corner_radius=24)
        settings.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        settings.grid_columnconfigure(0, weight=1)
        settings.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(settings, text="Settings", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))
        ctk.CTkButton(settings, text="Save Settings", command=self.save_settings).grid(row=0, column=1, sticky="e", padx=18, pady=(18, 10))

        self.require_admin_var = ctk.BooleanVar(value=self.controller.get_settings()["require_admin"])
        self.startup_var = ctk.BooleanVar(value=self.controller.get_settings()["start_with_windows"])
        self.block_taskmgr_var = ctk.BooleanVar(value=self.controller.get_settings()["block_task_manager"])
        self.openai_var = ctk.BooleanVar(value=self.controller.get_settings()["use_openai"])

        left = ctk.CTkFrame(settings, fg_color="#161d29", corner_radius=16)
        left.grid(row=1, column=0, sticky="nsew", padx=(18, 10), pady=(0, 18))
        ctk.CTkCheckBox(left, text="Require admin on launch", variable=self.require_admin_var).pack(anchor="w", padx=14, pady=(14, 8))
        ctk.CTkCheckBox(left, text="Auto start with Windows", variable=self.startup_var).pack(anchor="w", padx=14, pady=8)
        ctk.CTkCheckBox(left, text="Block Task Manager in focus", variable=self.block_taskmgr_var).pack(anchor="w", padx=14, pady=8)
        ctk.CTkCheckBox(left, text="Enable OpenAI classifier", variable=self.openai_var).pack(anchor="w", padx=14, pady=(8, 14))

        right = ctk.CTkFrame(settings, fg_color="#161d29", corner_radius=16)
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 18), pady=(0, 18))
        ctk.CTkLabel(right, text="OpenAI API Key").pack(anchor="w", padx=14, pady=(14, 6))
        self.api_key_entry = ctk.CTkEntry(right, show="*", placeholder_text="sk-...")
        self.api_key_entry.pack(fill="x", padx=14, pady=(0, 8))
        self.api_key_entry.insert(0, self.controller.get_settings()["openai_api_key"])
        ctk.CTkLabel(right, text="OpenAI Model").pack(anchor="w", padx=14, pady=(6, 6))
        self.model_entry = ctk.CTkEntry(right)
        self.model_entry.pack(fill="x", padx=14, pady=(0, 8))
        self.model_entry.insert(0, self.controller.get_settings()["openai_model"])
        ctk.CTkButton(right, text="Set / Change Settings Password", command=self.change_password).pack(fill="x", padx=14, pady=(8, 14))

    def start_focus(self) -> None:
        try:
            self.controller.start_focus(
                int(self.duration_var.get()),
                int(self.break_var.get()),
                bool(self.frozen_var.get()),
                bool(self.strict_var.get()),
            )
        except Exception as exc:
            messagebox.showerror("Start failed", str(exc))
        self.refresh_ui()

    def stop_focus(self) -> None:
        state = self.controller.get_session_state()
        if state.frozen_mode and state.is_active and not state.is_break:
            password = ctk.CTkInputDialog(text="Frozen focus is active. Enter settings password to force stop:", title="Protected Stop").get_input()
            if not password or not self.controller.verify_settings_password(password):
                messagebox.showerror("Denied", "Invalid password.")
                return
            self.controller.stop_focus(force=True)
        else:
            self.controller.stop_focus(force=True)
        self.refresh_ui()

    def add_rule(self) -> None:
        value = self.rule_value_entry.get().strip().lower()
        if not value:
            return
        self.controller.add_rule(value, self.rule_type_var.get(), self.rule_action_var.get())
        self.rule_value_entry.delete(0, "end")
        self.refresh_ui()

    def save_settings(self) -> None:
        if not self._settings_access_allowed():
            return
        self.controller.update_settings(
            {
                "require_admin": bool(self.require_admin_var.get()),
                "block_task_manager": bool(self.block_taskmgr_var.get()),
                "start_with_windows": bool(self.startup_var.get()),
                "use_openai": bool(self.openai_var.get()),
                "openai_api_key": self.api_key_entry.get().strip(),
                "openai_model": self.model_entry.get().strip() or "gpt-4.1-mini",
            }
        )
        messagebox.showinfo("Saved", "Settings updated.")

    def change_password(self) -> None:
        current_password = ctk.CTkInputDialog(text="Current password (leave blank if not set):", title="Current Password").get_input() or ""
        new_password = ctk.CTkInputDialog(text="New settings password:", title="New Password").get_input() or ""
        if not new_password:
            return
        success, message = self.controller.set_password(current_password, new_password)
        if success:
            messagebox.showinfo("Password", message)
        else:
            messagebox.showerror("Password", message)

    def _settings_access_allowed(self) -> bool:
        if self.controller.db.get_setting("settings_password_hash", ""):
            password = ctk.CTkInputDialog(text="Enter settings password:", title="Protected Settings").get_input()
            if not password or not self.controller.verify_settings_password(password):
                messagebox.showerror("Denied", "Invalid password.")
                return False
        return True

    def refresh_ui(self) -> None:
        stats = self.controller.get_stats()
        state = self.controller.get_session_state()
        rules = self.controller.get_rules()

        self.daily_card.set_value(f"{stats['daily_minutes'] // 60}h {stats['daily_minutes'] % 60}m")
        self.weekly_card.set_value(f"{stats['weekly_minutes'] // 60}h {stats['weekly_minutes'] % 60}m")
        self.streak_card.set_value(f"{stats['streak_days']} days")
        self.attempts_card.set_value(str(stats["distraction_attempts_today"]))

        self.activity_box.delete("1.0", "end")
        for event in stats["recent_events"]:
            self.activity_box.insert(
                "end",
                f"{event['created_at']} | {event['event_type']} | {event['message']}\n",
            )

        self.rules_box.delete("1.0", "end")
        self.rules_box.insert("end", "Allowed Sites\n")
        for item in rules["allowed_sites"]:
            self.rules_box.insert("end", f"  + {item}\n")
        self.rules_box.insert("end", "\nBlocked Sites\n")
        for item in rules["blocked_sites"]:
            self.rules_box.insert("end", f"  - {item}\n")
        self.rules_box.insert("end", "\nAllowed Apps\n")
        for item in rules["allowed_apps"]:
            self.rules_box.insert("end", f"  + {item}\n")
        self.rules_box.insert("end", "\nBlocked Apps\n")
        for item in rules["blocked_apps"]:
            self.rules_box.insert("end", f"  - {item}\n")

        if state.is_active:
            self.timer_label.configure(text=str(timedelta(seconds=state.seconds_remaining)))
            phase = "Break unlocked" if state.is_break else "Focus locked"
            self.status_label.configure(
                text=f"{phase} | Frozen={state.frozen_mode} | Strict={state.strict_whitelist}"
            )
        else:
            self.timer_label.configure(text="00:00:00")
            self.status_label.configure(text="Idle")

        self.after(1000, self.refresh_ui)


def main() -> None:
    """Entry point for the Study Lock GUI application."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=" * 60)
        logger.info("🎯 Study Lock Application Starting")
        logger.info("=" * 60)
        
        app = StudyLockApp()
        logger.info("✅ GUI initialized successfully")
        logger.info(f"🌐 API should be running on http://127.0.0.1:8765")
        logger.info(f"💻 Chrome Extension should connect within 30 seconds")
        logger.info("=" * 60)
        
        app.mainloop()
        
    except Exception as e:
        logger.error(f"❌ Application crashed: {e}", exc_info=True)
        raise
    finally:
        logger.info("=" * 60)
        logger.info("🛑 Study Lock Application Shutting Down")
        logger.info("=" * 60)
        
        try:
            from backend.api.server import stop_api_server
            stop_api_server()
            logger.info("API Server stopped")
        except Exception as e:
            logger.error(f"Error stopping API server: {e}")
