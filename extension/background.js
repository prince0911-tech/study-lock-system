const API_BASE = "http://127.0.0.1:8765";
const API_HEALTH_CHECK = `${API_BASE}/health`;
const MAX_RETRIES = 3;
const RETRY_DELAY = 500; // ms
const HEALTH_CHECK_INTERVAL = 5000; // ms

// Track API connectivity state
let isAPIAvailable = false;
let lastHealthCheck = 0;

/**
 * Check if API is available with caching
 */
async function checkAPIHealth() {
  const now = Date.now();
  if (now - lastHealthCheck < 1000) {
    // Use cached result if check was recent
    return isAPIAvailable;
  }

  try {
    const response = await Promise.race([
      fetch(API_HEALTH_CHECK, { method: "GET" }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("Timeout")), 3000)
      )
    ]);

    isAPIAvailable = response.ok;
    lastHealthCheck = now;

    if (isAPIAvailable) {
      console.log("✅ Study Lock API is available");
    } else {
      console.warn("⚠️ Study Lock API returned error:", response.status);
    }
    return isAPIAvailable;
  } catch (error) {
    isAPIAvailable = false;
    lastHealthCheck = now;
    console.warn("⚠️ Study Lock API unavailable:", error.message);
    return false;
  }
}

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
      console.log(
        `🔄 Retry ${retryCount + 1}/${MAX_RETRIES} for ${endpoint}: ${error.message}`
      );
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (retryCount + 1)));
      return makeAPIRequest(endpoint, options, retryCount + 1);
    }

    console.error(`❌ Failed to fetch ${endpoint}:`, error.message);
    throw error;
  }
}

/**
 * Get current session status with health check
 */
async function getSessionStatus() {
  try {
    // Check health first
    const isHealthy = await checkAPIHealth();
    if (!isHealthy) {
      return null;
    }

    return await makeAPIRequest(`${API_BASE}/api/session/status`);
  } catch (error) {
    console.warn("Failed to get session status:", error);
    return null;
  }
}

/**
 * Evaluate tab for blocking with retry logic
 */
async function evaluateTab(tab) {
  if (!tab || !tab.url || !/^https?:/.test(tab.url)) {
    return;
  }

  try {
    // Check if focus session is active
    const session = await getSessionStatus();
    if (!session || !session.is_active || session.is_break) {
      return;
    }

    // Evaluate the tab
    const result = await makeAPIRequest(`${API_BASE}/api/browser/evaluate`, {
      method: "POST",
      body: {
        url: tab.url,
        title: tab.title || "",
        page_text: "",
        source: "chrome-extension"
      }
    });

    if (result.decision === "BLOCK") {
      const reason = result.reason || "Content blocked during focus mode";
      const blockedUrl = chrome.runtime.getURL("blocked.html") +
        `?target=${encodeURIComponent(tab.url)}&reason=${encodeURIComponent(reason)}`;
      chrome.tabs.update(tab.id, { url: blockedUrl });
    }
  } catch (error) {
    console.warn("Error evaluating tab:", error);
  }
}

/**
 * Handle tab activation
 */
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    evaluateTab(tab);
  } catch (error) {
    console.error("Error handling tab activation:", error);
  }
});

/**
 * Handle tab updates
 */
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    evaluateTab(tab);
  }
});

/**
 * Handle messages from content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "YOUTUBE_CONTEXT" && sender.tab) {
    makeAPIRequest(`${API_BASE}/api/browser/evaluate`, {
      method: "POST",
      body: {
        url: sender.tab.url || "",
        title: message.title || sender.tab.title || "",
        page_text: message.pageText || "",
        source: "youtube-content"
      }
    })
      .then(result => sendResponse(result || { decision: "ALLOW" }))
      .catch(error => {
        console.warn("Error evaluating YouTube content:", error);
        sendResponse({ decision: "ALLOW" });
      });
    return true;
  }
  return false;
});

/**
 * Periodic health check
 */
setInterval(async () => {
  await checkAPIHealth();
}, HEALTH_CHECK_INTERVAL);

// Initial health check
checkAPIHealth();
