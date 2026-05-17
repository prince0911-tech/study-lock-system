const API_BASE = "http://127.0.0.1:8765";
const API_HEALTH_CHECK = `${API_BASE}/health`;
const MAX_RETRIES = 2;
const RETRY_DELAY = 300; // ms

/**
 * Make API request with retry logic
 */
async function makeAPIRequest(endpoint, options = {}, retryCount = 0) {
  try {
    const { method = "GET", body = null, timeout = 5000 } = options;

    const fetchOptions = {
      method,
      headers: { "Content-Type": "application/json" },
      ...(body && { body: JSON.stringify(body) })
    };

    const response = await Promise.race([
      fetch(endpoint, fetchOptions),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("Request timeout")), timeout)
      )
    ]);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (retryCount < MAX_RETRIES) {
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (retryCount + 1)));
      return makeAPIRequest(endpoint, options, retryCount + 1);
    }
    throw error;
  }
}

/**
 * Load and display status
 */
async function loadStatus() {
  const statusNode = document.getElementById("status");
  const modeNode = document.getElementById("mode");
  const timeNode = document.getElementById("time");

  try {
    // Try to get session status
    const state = await makeAPIRequest(`${API_BASE}/api/session/status`);

    if (state.error) {
      throw new Error(state.error);
    }

    // Update UI with live data
    statusNode.textContent = "✅ Connected to desktop app";
    statusNode.style.color = "#22c55e"; // Green

    modeNode.textContent = state.is_active
      ? (state.is_break ? "Mode: Break 🌟" : "Mode: Focus 🔒")
      : "Mode: Idle ⏸️";

    // Format remaining time
    const hours = Math.floor(state.seconds_remaining / 3600);
    const minutes = Math.floor((state.seconds_remaining % 3600) / 60);
    const seconds = state.seconds_remaining % 60;
    const timeStr = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    timeNode.textContent = timeStr;

  } catch (error) {
    // API is unavailable
    statusNode.textContent = "⚠️ Desktop app offline";
    statusNode.style.color = "#ef4444"; // Red
    modeNode.textContent = "Mode: Unknown";
    timeNode.textContent = "--:--:--";

    console.warn("Failed to connect to API:", error.message);
  }
}

/**
 * Initialize popup
 */
async function initPopup() {
  // Load initial status
  await loadStatus();

  // Update every 1 second
  setInterval(loadStatus, 1000);
}

// Initialize when popup opens
document.addEventListener("DOMContentLoaded", initPopup);
