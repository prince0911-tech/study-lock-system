# Architecture Notes

## Runtime components

- `desktop_app.study_lock_gui`
  Hosts the dashboard, launches the local API, and controls focus sessions.
- `backend.api.server`
  Exposes localhost endpoints consumed by the dashboard and Chrome extension.
- `backend.services.process_monitor`
  Scans running processes and terminates blocked or non-whitelisted user applications during focus.
- `backend.services.classifier`
  Performs rule-based, keyword-based, and optional OpenAI tab classification.
- `extension/background.js`
  Evaluates tabs on load and redirects blocked pages.
- `extension/content.js`
  Removes distracting YouTube UI elements and sends additional page context for classification.

## Persistence

- SQLite stores sessions, attempts, rules, settings, and system events.
- Encrypted settings snapshots are written to `runtime/config/settings.enc`.
- Runtime focus state is written to `runtime/state/runtime_state.json` for watchdog recovery.

## Threat model

- This app is intended to resist casual bypassing by the signed-in user.
- It does not prevent a determined admin from deleting files, editing the registry, or terminating Python at the OS level.
- For stronger enforcement, move the monitor into a Windows service and add signed binaries plus tamper protection.
