# Study Lock System

Study Lock System is a Windows-focused productivity lock environment built with Python, CustomTkinter, SQLite, `psutil`, `pywin32`, and a Chrome Manifest V3 extension. During a focus session it enforces study-only rules by terminating blocked applications, evaluating browser tabs against allow/block policies, classifying unknown pages as study or distraction, and unlocking a break window only after the study timer completes.

## Architecture Overview

The system has three runtime layers:

1. Desktop control app
   Runs the CustomTkinter dashboard, launches the local API, starts the watchdog, and exposes session controls.
2. Local enforcement backend
   Maintains the SQLite database, focus session state, rule engine, AI classifier, Windows startup integration, encrypted settings, logging, and process monitoring.
3. Chrome extension
   Calls the local API on tab updates, blocks distracting pages, and removes distracting YouTube elements like Shorts, comments, and recommendations.

### Data flow

1. The user starts a focus session in the desktop app.
2. The backend creates a focus session row in SQLite and begins countdown tracking.
3. The process monitor continuously scans Windows processes and terminates blocked or non-whitelisted apps.
4. The extension sends URL and title data to `http://127.0.0.1:8765/api/browser/evaluate`.
5. The classifier returns `STUDY` or `DISTRACTION`.
6. The extension either allows the page or redirects to `blocked.html`.
7. When the focus timer completes, the backend creates a break session and unlocks browsing until the break expires.

## Folder Structure

```text
study-lock-system/
├── assets/
├── backend/
│   ├── api/
│   │   └── server.py
│   ├── core/
│   │   ├── constants.py
│   │   ├── logging_config.py
│   │   ├── paths.py
│   │   └── security.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── classifier.py
│   │   ├── database.py
│   │   ├── policy.py
│   │   ├── process_monitor.py
│   │   ├── session_manager.py
│   │   ├── watchdog.py
│   │   └── windows_control.py
│   ├── app_controller.py
│   └── watchdog_runner.py
├── database/
│   ├── schema.sql
│   └── study_lock.db
├── desktop_app/
│   ├── main.py
│   └── study_lock_gui.py
├── docs/
├── extension/
│   ├── background.js
│   ├── blocked.css
│   ├── blocked.html
│   ├── content.js
│   ├── manifest.json
│   ├── popup.css
│   ├── popup.html
│   └── popup.js
├── installer/
│   └── StudyLock.spec
├── logs/
├── runtime/
├── build_exe.bat
├── requirements.txt
├── run.bat
└── setup.bat
```

## Implementation Roadmap

1. Install Python dependencies and initialize the SQLite database.
2. Run the desktop app so the local API and monitor threads start.
3. Load the Chrome extension in developer mode.
4. Review and customize default allow/block rules in the dashboard.
5. Set a settings password before using frozen mode.
6. Optionally add an OpenAI API key for AI classification of ambiguous pages.
7. Package the app with PyInstaller after local validation.

## Features

### Focus mode

- Starts timed focus sessions and automatic reward break sessions.
- Supports frozen mode that requires a password to force stop.
- Supports strict whitelist mode to terminate non-approved user applications.
- Continuously logs blocked attempts and system events.

### Windows monitoring

- Terminates blocked applications using `psutil`.
- Supports autorun through the `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry key.
- Includes a watchdog helper to relaunch the GUI when a protected session is active.
- Includes Task Manager blocking through the blocked app list and monitor loop.

### AI website classification

- Rule-first decision engine: explicit allow/block rules override everything.
- Keyword fallback classifier works with no API key.
- Optional OpenAI classification for ambiguous tabs.
- Unknown content defaults to blocked during active focus sessions.

### Chrome extension

- Evaluates tabs on activation and load completion.
- Redirects blocked tabs to a local extension block screen.
- Sends YouTube page content to the desktop app for finer classification.
- Removes YouTube homepage recommendations, Shorts, comments, and sidebar suggestions.

### Security and persistence

- Settings are mirrored to an encrypted snapshot in `runtime/config/settings.enc`.
- Settings password is stored as a bcrypt hash in SQLite.
- Logs are written to `logs/study_lock.log` and `logs/crash.log`.

## Installation

### Prerequisites

- Windows 10 or Windows 11
- Python 3.12+ installed and available as `python`
- Google Chrome
- Administrator privileges recommended for stronger process termination and firewall configuration

### Setup

1. Open PowerShell in the project root.
2. Run:

```bat
setup.bat
```

3. Start the app:

```bat
run.bat
```

4. Open Chrome at `chrome://extensions`.
5. Enable Developer Mode.
6. Click `Load unpacked`.
7. Select the `extension` folder from this project.

## How To Use

1. Launch `run.bat`.
2. Open the dashboard.
3. Set a settings password.
4. Review the default allowed apps and websites.
5. Start a focus session.
6. During focus:
   The backend enforces process rules.
   The extension blocks non-study pages.
7. After the study timer ends, a break session starts automatically.

## Default Policy Behavior

- Allowed apps include `code.exe`, `chrome.exe`, `notion.exe`, `jupyter-lab.exe`, and other common study tools.
- Blocked apps include `discord.exe`, `steam.exe`, `spotify.exe`, `vlc.exe`, and `taskmgr.exe`.
- Allowed sites include ChatGPT, GitHub, Stack Overflow, Kaggle, Python docs, YouTube, and learning platforms.
- Blocked sites include Instagram, Reddit, Netflix, Discord, and major social platforms.
- Unknown websites are blocked during focus unless the classifier identifies them as study-oriented.

## Packaging To EXE

### Build command

```bat
build_exe.bat
```

The generated executable will be placed under `dist\StudyLock`.

### Notes

- The PyInstaller spec bundles the extension and schema assets.
- Test the packaged build with Chrome extension loading and autorun before using it as your primary install.
- If Windows Defender or SmartScreen flags an unsigned build, sign the executable for smoother deployment.

## Screenshots

Add screenshots here after first run:

- Dashboard overview
- Rule manager
- Settings area
- Chrome blocked page

## Troubleshooting

### The extension says the desktop app is offline

- Confirm `run.bat` is still running.
- Confirm the local API is reachable at `http://127.0.0.1:8765/health`.
- Check `logs/study_lock.log`.

### Apps are not terminating

- Run the app with administrator privileges.
- Confirm the executable names match the real process names in Task Manager.
- Disable strict whitelist if a required study tool is being terminated unexpectedly.

### A study site is being blocked

- Add the domain to the allow list in the rule manager.
- If it is a YouTube page, check the title and content classification behavior.

### Frozen mode cannot be stopped

- Use the settings password.
- If you forgot the password, stop the app and manually remove the `settings_password_hash` row from SQLite.

## Security Notes

- This project raises the difficulty of bypassing focus mode but does not act as kernel-level device lockdown.
- Users with full admin access can still alter registry entries, delete files, or terminate Python before the watchdog reacts.
- Stronger tamper resistance would require a signed Windows service running with elevated privileges and tighter OS policy controls.

## Future Improvements

- Replace the watchdog helper with a proper Windows service.
- Add WebSocket push updates for the extension instead of request polling.
- Add per-category analytics and charts.
- Add OCR or local LLM page classification.
- Add tray mode and multi-browser support.
