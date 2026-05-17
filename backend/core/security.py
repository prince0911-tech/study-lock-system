from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import bcrypt
from cryptography.fernet import Fernet

from .paths import SECRET_KEY_PATH, ensure_directories


def get_or_create_fernet() -> Fernet:
    ensure_directories()
    if not SECRET_KEY_PATH.exists():
        SECRET_KEY_PATH.write_bytes(Fernet.generate_key())
    return Fernet(SECRET_KEY_PATH.read_bytes())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def encrypt_json(data: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    token = get_or_create_fernet().encrypt(json.dumps(data).encode("utf-8"))
    destination.write_bytes(token)


def decrypt_json(source: Path) -> dict[str, Any]:
    if not source.exists():
        return {}
    payload = get_or_create_fernet().decrypt(source.read_bytes())
    return json.loads(payload.decode("utf-8"))
