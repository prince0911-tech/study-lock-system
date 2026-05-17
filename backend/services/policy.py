from __future__ import annotations

from urllib.parse import urlparse

from backend.services.database import DatabaseManager


class PolicyManager:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def load_rules(self) -> dict[str, list[str]]:
        return self.db.list_rules()

    def is_domain_allowed(self, url: str) -> tuple[bool, str | None]:
        domain = self._normalize_domain(url)
        rules = self.load_rules()
        if any(domain == item or domain.endswith(f".{item}") for item in rules["blocked_sites"]):
            return False, domain
        if any(domain == item or domain.endswith(f".{item}") for item in rules["allowed_sites"]):
            return True, domain
        return False, None

    def is_process_allowed(self, process_name: str) -> tuple[bool, str | None]:
        normalized = process_name.lower()
        rules = self.load_rules()
        if normalized in rules["blocked_apps"]:
            return False, normalized
        if normalized in rules["allowed_apps"]:
            return True, normalized
        return False, None

    @staticmethod
    def _normalize_domain(url: str) -> str:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc.lower().replace("www.", "")
