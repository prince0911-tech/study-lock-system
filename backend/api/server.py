from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable

from flask import Flask, jsonify, request
from werkzeug.serving import make_server
from werkzeug.exceptions import BadRequest

from backend.app_controller import AppController
from backend.core.constants import API_HOST, API_PORT

logger = logging.getLogger(__name__)

# Global reference to track server state
_server: make_server | None = None
_server_thread: threading.Thread | None = None
_server_lock = threading.Lock()
_server_ready = threading.Event()


def create_api(controller: AppController) -> Flask:
    """Create and configure Flask application with all endpoints."""
    app = Flask(__name__)
    
    # CORS handling
    @app.before_request
    def handle_cors():
        origin = request.headers.get("Origin")
        if origin and (
            origin.startswith("http://127.0.0.1") 
            or origin.startswith("http://localhost")
            or origin.startswith("chrome-extension://")
        ):
            pass  # Allow
        if request.method == "OPTIONS":
            response = jsonify({"status": "ok"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Methods", "*")
            response.headers.add("Access-Control-Allow-Headers", "*")
            return response, 200

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and (
            origin.startswith("http://127.0.0.1") 
            or origin.startswith("http://localhost")
            or origin.startswith("chrome-extension://")
        ):
            response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Methods", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response

    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health() -> tuple[dict[str, str], int]:
        """Health check endpoint for server readiness verification."""
        logger.debug("Health check requested")
        return {"status": "ok", "timestamp": str(time.time())}, 200

    # Rules endpoints
    @app.route("/api/rules", methods=["GET"])
    def get_rules() -> tuple[dict, int]:
        """Get all blocking rules."""
        try:
            rules = controller.get_rules()
            return rules, 200
        except Exception as e:
            logger.error(f"Error getting rules: {e}")
            return {"error": str(e)}, 500

    @app.route("/api/rules", methods=["POST"])
    def upsert_rule() -> tuple[dict[str, str], int]:
        """Add or update a rule."""
        try:
            data = request.get_json()
            if not data:
                return {"error": "No JSON data provided"}, 400
            controller.add_rule(data["value"], data["rule_type"], data["action"])
            return {"status": "ok"}, 200
        except Exception as e:
            logger.error(f"Error upserting rule: {e}")
            return {"error": str(e)}, 500

    @app.route("/api/rules/<path:value>", methods=["DELETE"])
    def delete_rule(value: str) -> tuple[dict[str, str], int]:
        """Delete a rule."""
        try:
            controller.delete_rule(value)
            return {"status": "ok"}, 200
        except Exception as e:
            logger.error(f"Error deleting rule: {e}")
            return {"error": str(e)}, 500

    # Session endpoints
    @app.route("/api/session/start", methods=["POST"])
    def start_session() -> tuple[dict, int]:
        """Start a focus session."""
        try:
            data = request.get_json()
            if not data:
                return {"error": "No JSON data provided"}, 400
            state = controller.start_focus(
                data.get("duration_minutes", 90),
                data.get("break_minutes", 15),
                data.get("frozen_mode", True),
                data.get("strict_whitelist", True),
            )
            return state.__dict__, 200
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return {"error": str(e)}, 500

    @app.route("/api/session/stop", methods=["POST"])
    def stop_session() -> tuple[dict, int]:
        """Stop the current focus session."""
        try:
            force = request.args.get("force", "false").lower() == "true"
            state = controller.stop_focus(force=force)
            return state.__dict__, 200
        except Exception as e:
            logger.error(f"Error stopping session: {e}")
            return {"error": str(e)}, 500

    @app.route("/api/session/status", methods=["GET"])
    def session_status() -> tuple[dict, int]:
        """Get current session status."""
        try:
            state = controller.get_session_state()
            return state.__dict__, 200
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return {"error": str(e)}, 500

    # Browser evaluation endpoint
    @app.route("/api/browser/evaluate", methods=["POST"])
    def evaluate_browser() -> tuple[dict, int]:
        """Evaluate browser content for blocking."""
        try:
            data = request.get_json()
            if not data:
                return {"error": "No JSON data provided"}, 400
            result = controller.evaluate_browser_content(
                data.get("url", ""),
                data.get("title", ""),
                data.get("page_text", ""),
            )
            return result.__dict__, 200
        except Exception as e:
            logger.error(f"Error evaluating browser content: {e}")
            return {"error": str(e)}, 500

    # Stats endpoint
    @app.route("/api/stats", methods=["GET"])
    def get_stats() -> tuple[dict, int]:
        """Get system statistics."""
        try:
            stats = controller.get_stats()
            return stats, 200
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}, 500

    # Settings endpoints
    @app.route("/api/settings", methods=["GET"])
    def get_settings() -> tuple[dict, int]:
        """Get application settings."""
        try:
            settings = controller.get_settings()
            return settings, 200
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return {"error": str(e)}, 500

    @app.route("/api/settings", methods=["POST"])
    def update_settings() -> tuple[dict[str, str], int]:
        """Update application settings."""
        try:
            data = request.get_json()
            if not data:
                return {"error": "No JSON data provided"}, 400
            controller.update_settings(data)
            return {"status": "ok"}, 200
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return {"error": str(e)}, 500

    @app.route("/api/settings/password", methods=["POST"])
    def update_password() -> tuple[dict[str, str], int]:
        """Update settings password."""
        try:
            data = request.get_json()
            if not data:
                return {"error": "No JSON data provided"}, 400
            success, message = controller.set_password(
                data.get("current_password", ""),
                data.get("new_password", ""),
            )
            if not success:
                return {"error": message}, 403
            return {"status": "ok", "message": message}, 200
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return {"error": str(e)}, 500

    # Error handler
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {"error": "Internal server error"}, 500

    logger.info("Flask application created successfully")
    return app


def start_api_server(controller: AppController, timeout: int = 10) -> bool:
    """
    Start the API server in a background thread with startup verification.
    
    Args:
        controller: The AppController instance
        timeout: Maximum seconds to wait for server startup
        
    Returns:
        True if server started successfully, False otherwise
    """
    global _server, _server_thread, _server_ready
    
    _server_ready.clear()
    
    def run_server():
        global _server
        try:
            app = create_api(controller)
            _server = make_server(API_HOST, API_PORT, app, threaded=True)
            logger.info(f"🚀 API Server starting on {API_HOST}:{API_PORT}")
            logger.info(f"Health check URL: http://{API_HOST}:{API_PORT}/health")
            _server_ready.set()
            _server.serve_forever()
        except Exception as e:
            logger.error(f"❌ API Server startup failed: {e}", exc_info=True)
            _server_ready.set()  # Still set to unblock main thread

    with _server_lock:
        if _server_thread and _server_thread.is_alive():
            logger.warning("API Server already running")
            return True

        _server_thread = threading.Thread(
            target=run_server,
            daemon=False,
            name="APIServerThread"
        )
        _server_thread.start()

    # Wait for server to be ready or timeout
    if _server_ready.wait(timeout=timeout):
        if _server is None:
            logger.error("Server initialization failed")
            return False
        logger.info("✅ API Server ready and accepting connections")
        return True
    else:
        logger.error(f"API Server startup timeout after {timeout} seconds")
        return False


def stop_api_server() -> None:
    """Gracefully stop the API server."""
    global _server, _server_thread
    
    with _server_lock:
        if _server:
            try:
                logger.info("Shutting down API server...")
                _server.shutdown()
                _server = None
            except Exception as e:
                logger.error(f"Error shutting down server: {e}")
        
        if _server_thread and _server_thread.is_alive():
            _server_thread.join(timeout=5)
            if _server_thread.is_alive():
                logger.warning("Server thread did not stop cleanly")


def run_api(controller: AppController) -> None:
    """Legacy entry point for backward compatibility."""
    start_api_server(controller)
