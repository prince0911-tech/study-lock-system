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
