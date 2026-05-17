"""
Reconnect-safe API client with automatic retry logic.

This module provides a robust API client that:
- Automatically retries failed requests
- Verifies API connectivity before operations
- Handles graceful degradation
- Provides detailed logging
- Implements exponential backoff
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default configuration
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8765
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 0.5  # seconds
DEFAULT_RETRY_BACKOFF = 1.5  # exponential backoff factor


class APIConnectionError(Exception):
    """Raised when API connection fails after retries."""
    pass


class APIError(Exception):
    """Raised when API returns an error."""
    pass


class StudyLockAPIClient:
    """
    Reconnect-safe client for Study Lock API.
    
    Features:
    - Automatic connection verification
    - Exponential backoff retry logic
    - Graceful error handling
    - Detailed logging for debugging
    - Connection state tracking
    """

    def __init__(
        self,
        host: str = DEFAULT_API_HOST,
        port: int = DEFAULT_API_PORT,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ):
        """
        Initialize the API client.

        Args:
            host: API host address
            port: API port number
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff applied)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.base_url = f"http://{host}:{port}"
        self._is_connected = False
        self._last_error = None

    def is_available(self) -> bool:
        """Check if API is available via health check."""
        try:
            response = self._make_request("GET", "/health", retries=1)
            self._is_connected = response.get("status") == "ok"
            if self._is_connected:
                logger.debug("✅ API is available")
            return self._is_connected
        except Exception as e:
            self._is_connected = False
            self._last_error = str(e)
            logger.debug(f"⚠️ API unavailable: {e}")
            return False

    def wait_for_api(self, timeout: int = 30, poll_interval: float = 0.5) -> bool:
        """
        Wait for API to become available.

        Args:
            timeout: Maximum time to wait in seconds
            poll_interval: Time between health checks in seconds

        Returns:
            True if API became available, False if timeout
        """
        start_time = time.time()
        attempt = 0

        while time.time() - start_time < timeout:
            attempt += 1
            logger.info(f"🔄 Waiting for API... (attempt {attempt})")

            if self.is_available():
                logger.info(f"✅ API available after {time.time() - start_time:.1f}s")
                return True

            time.sleep(poll_interval)

        logger.error(f"❌ API not available after {timeout}s timeout")
        return False

    def get_rules(self) -> dict[str, Any]:
        """Get all blocking rules."""
        try:
            return self._make_request("GET", "/api/rules")
        except Exception as e:
            logger.error(f"Error fetching rules: {e}")
            return {"allowed_sites": [], "blocked_sites": [], "allowed_apps": [], "blocked_apps": []}

    def add_rule(self, value: str, rule_type: str, action: str) -> bool:
        """Add or update a rule."""
        try:
            payload = {"value": value, "rule_type": rule_type, "action": action}
            self._make_request("POST", "/api/rules", json=payload)
            return True
        except Exception as e:
            logger.error(f"Error adding rule: {e}")
            return False

    def delete_rule(self, value: str) -> bool:
        """Delete a rule."""
        try:
            self._make_request("DELETE", f"/api/rules/{value}")
            return True
        except Exception as e:
            logger.error(f"Error deleting rule: {e}")
            return False

    def start_session(
        self,
        duration_minutes: int = 90,
        break_minutes: int = 15,
        frozen_mode: bool = True,
        strict_whitelist: bool = True,
    ) -> dict[str, Any]:
        """Start a focus session."""
        try:
            payload = {
                "duration_minutes": duration_minutes,
                "break_minutes": break_minutes,
                "frozen_mode": frozen_mode,
                "strict_whitelist": strict_whitelist,
            }
            return self._make_request("POST", "/api/session/start", json=payload)
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return {"error": str(e)}

    def stop_session(self, force: bool = False) -> dict[str, Any]:
        """Stop the current focus session."""
        try:
            return self._make_request("POST", f"/api/session/stop?force={str(force).lower()}")
        except Exception as e:
            logger.error(f"Error stopping session: {e}")
            return {"error": str(e)}

    def get_session_status(self) -> dict[str, Any]:
        """Get current session status."""
        try:
            return self._make_request("GET", "/api/session/status")
        except Exception as e:
            logger.error(f"Error fetching session status: {e}")
            return {"error": str(e), "is_active": False}

    def evaluate_browser(self, url: str, title: str, page_text: str = "") -> dict[str, Any]:
        """Evaluate browser content for blocking."""
        try:
            payload = {"url": url, "title": title, "page_text": page_text}
            return self._make_request("POST", "/api/browser/evaluate", json=payload)
        except Exception as e:
            logger.error(f"Error evaluating browser content: {e}")
            # Safe default: allow if we can't reach API
            return {
                "decision": "ALLOW",
                "category": "UNKNOWN",
                "reason": "API unavailable",
                "confidence": 0.0,
            }

    def get_stats(self) -> dict[str, Any]:
        """Get system statistics."""
        try:
            return self._make_request("GET", "/api/stats")
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return {}

    def get_settings(self) -> dict[str, Any]:
        """Get application settings."""
        try:
            return self._make_request("GET", "/api/settings")
        except Exception as e:
            logger.error(f"Error fetching settings: {e}")
            return {}

    def update_settings(self, settings: dict[str, Any]) -> bool:
        """Update application settings."""
        try:
            self._make_request("POST", "/api/settings", json=settings)
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False

    def update_password(self, current_password: str, new_password: str) -> tuple[bool, str]:
        """Update settings password."""
        try:
            payload = {
                "current_password": current_password,
                "new_password": new_password,
            }
            result = self._make_request("POST", "/api/settings/password", json=payload)
            return True, result.get("message", "Password updated")
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False, str(e)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[dict] = None,
        retries: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request with automatic retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            json: JSON payload for request
            retries: Override max_retries for this request

        Returns:
            Response data as dictionary

        Raises:
            APIConnectionError: If connection fails after retries
            APIError: If API returns an error
        """
        if retries is None:
            retries = self.max_retries

        url = f"{self.base_url}{endpoint}"
        last_error = None
        delay = self.retry_delay

        for attempt in range(retries):
            try:
                import urllib.request
                import urllib.error

                headers = {"Content-Type": "application/json"}
                data = None

                if json:
                    data = json_encode(json).encode("utf-8")

                request = urllib.request.Request(
                    url, data=data, headers=headers, method=method
                )

                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    response_data = response.read().decode("utf-8")
                    return json_decode(response_data) if response_data else {}

            except urllib.error.URLError as e:
                last_error = f"Connection failed: {e.reason}"
                if attempt < retries - 1:
                    logger.debug(f"Retry {attempt + 1}/{retries} after {delay}s: {last_error}")
                    time.sleep(delay)
                    delay *= DEFAULT_RETRY_BACKOFF
                continue

            except urllib.error.HTTPError as e:
                response_data = e.read().decode("utf-8")
                try:
                    error_json = json_decode(response_data)
                    error_msg = error_json.get("error", str(e))
                except:
                    error_msg = response_data or str(e)

                if e.code >= 500:
                    last_error = f"Server error ({e.code}): {error_msg}"
                    if attempt < retries - 1:
                        logger.debug(f"Retry {attempt + 1}/{retries} after {delay}s: {last_error}")
                        time.sleep(delay)
                        delay *= DEFAULT_RETRY_BACKOFF
                    continue
                else:
                    raise APIError(f"{method} {endpoint}: {e.code} {error_msg}")

            except Exception as e:
                last_error = f"Unexpected error: {e}"
                if attempt < retries - 1:
                    logger.debug(f"Retry {attempt + 1}/{retries} after {delay}s: {last_error}")
                    time.sleep(delay)
                    delay *= DEFAULT_RETRY_BACKOFF
                continue

        raise APIConnectionError(f"Failed after {retries} attempts: {last_error}")


def json_encode(obj: Any) -> str:
    """Encode object to JSON."""
    return json.dumps(obj, default=str)


def json_decode(text: str) -> dict:
    """Decode JSON string."""
    return json.loads(text)


# Global client instance
_client: Optional[StudyLockAPIClient] = None


def get_client() -> StudyLockAPIClient:
    """Get or create the global API client."""
    global _client
    if _client is None:
        _client = StudyLockAPIClient()
    return _client


def set_client(client: StudyLockAPIClient) -> None:
    """Set the global API client."""
    global _client
    _client = client
