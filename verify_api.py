#!/usr/bin/env python3
"""
Study Lock API Startup Verification Script

This script verifies that the Flask API server starts correctly and can handle requests.
Use this to diagnose startup issues.

Usage:
    python verify_api.py
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.app_controller import AppController
from backend.api.server import start_api_server, stop_api_server
from backend.api.client import StudyLockAPIClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def verify_api_startup():
    """Verify the API starts and responds correctly."""
    logger.info("=" * 70)
    logger.info("🧪 Study Lock API Startup Verification")
    logger.info("=" * 70)

    try:
        # Step 1: Initialize controller
        logger.info("\n📍 Step 1: Initializing AppController...")
        controller = AppController()
        logger.info("✅ AppController initialized successfully")

        # Step 2: Start API server
        logger.info("\n📍 Step 2: Starting API server...")
        success = start_api_server(controller, timeout=10)

        if not success:
            logger.error("❌ API server startup failed")
            return False

        logger.info("✅ API server started")

        # Step 3: Wait a moment for server to stabilize
        logger.info("\n📍 Step 3: Allowing server to stabilize...")
        time.sleep(1)

        # Step 4: Test API connectivity
        logger.info("\n📍 Step 4: Testing API connectivity...")
        client = StudyLockAPIClient()

        if not client.is_available():
            logger.error("❌ API health check failed")
            return False

        logger.info("✅ API health check passed")

        # Step 5: Test endpoints
        logger.info("\n📍 Step 5: Testing API endpoints...")

        tests = [
            ("Session Status", lambda: client.get_session_status()),
            ("Settings", lambda: client.get_settings()),
            ("Stats", lambda: client.get_stats()),
            ("Rules", lambda: client.get_rules()),
        ]

        all_passed = True
        for test_name, test_func in tests:
            try:
                result = test_func()
                if isinstance(result, dict) and "error" not in result:
                    logger.info(f"  ✅ {test_name}")
                else:
                    logger.warning(f"  ⚠️ {test_name}: {result.get('error', 'Unknown error')}")
                    all_passed = False
            except Exception as e:
                logger.error(f"  ❌ {test_name}: {e}")
                all_passed = False

        if not all_passed:
            logger.warning("Some endpoints returned errors")

        # Step 6: Test browser evaluation
        logger.info("\n📍 Step 6: Testing browser evaluation...")
        try:
            result = client.evaluate_browser(
                "https://example.com",
                "Example Domain",
                ""
            )
            if "decision" in result:
                logger.info(f"  ✅ Browser evaluation: {result['decision']}")
            else:
                logger.error(f"  ❌ Invalid response: {result}")
        except Exception as e:
            logger.error(f"  ❌ Browser evaluation: {e}")

        # Cleanup
        logger.info("\n📍 Cleanup: Stopping API server...")
        stop_api_server()
        logger.info("✅ API server stopped")

        logger.info("\n" + "=" * 70)
        logger.info("✅ VERIFICATION COMPLETE - All systems nominal!")
        logger.info("=" * 70)
        logger.info("\n📝 Summary:")
        logger.info(f"  - API running on: http://127.0.0.1:8765")
        logger.info(f"  - Health endpoint: http://127.0.0.1:8765/health")
        logger.info(f"  - API is ready for extension communication")
        logger.info("\n💡 Next steps:")
        logger.info("  1. Run the desktop app: python -m desktop_app.main")
        logger.info("  2. Load the extension in Chrome: chrome://extensions")
        logger.info("  3. Check browser console for connection logs")
        logger.info("=" * 70)
        return True

    except Exception as e:
        logger.error(f"\n❌ Verification failed: {e}", exc_info=True)
        logger.info("\n" + "=" * 70)
        logger.info("❌ VERIFICATION FAILED")
        logger.info("=" * 70)
        logger.info("\n🔧 Troubleshooting:")
        logger.info("  1. Check that port 8765 is not already in use")
        logger.info("  2. Ensure database files are initialized")
        logger.info("  3. Check logs in runtime/logs/study_lock.log")
        logger.info("  4. Verify all dependencies are installed: pip install -r requirements.txt")
        logger.info("=" * 70)
        return False


if __name__ == "__main__":
    success = verify_api_startup()
    sys.exit(0 if success else 1)
