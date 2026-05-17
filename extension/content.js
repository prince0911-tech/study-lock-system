const API_BASE = "http://127.0.0.1:8765";
const MAX_RETRIES = 2;
const RETRY_DELAY = 300; // ms

/**
 * Remove YouTube distractions
 */
function removeYouTubeDistractions() {
  const selectors = [
    "ytd-rich-grid-renderer",
    "ytd-reel-shelf-renderer",
    "ytd-shorts",
    "#comments",
    "#related",
    "ytd-watch-next-secondary-results-renderer",
    "ytd-mini-guide-renderer a[title='Shorts']",
    "a[title='Shorts']"
  ];
  selectors.forEach((selector) => {
    document.querySelectorAll(selector).forEach((node) => {
      node.style.display = "none";
    });
  });
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
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (retryCount + 1)));
      return makeAPIRequest(endpoint, options, retryCount + 1);
    }
    throw error;
  }
}

/**
 * Send page context for evaluation
 */
function sendContext() {
  const title = document.title || "";
  const pageText = document.body?.innerText?.slice(0, 1000) || "";

  chrome.runtime.sendMessage({
    type: "YOUTUBE_CONTEXT",
    title,
    pageText
  }, async (result) => {
    if (chrome.runtime.lastError) {
      console.warn("Extension error:", chrome.runtime.lastError);
      return;
    }

    if (result?.decision === "BLOCK") {
      // Block the content with a styled message
      const reason = result.reason || "Content blocked during focus mode";
      document.body.innerHTML = `
        <div style="font-family:Segoe UI,sans-serif;background:#090b10;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;">
          <div style="max-width:720px;background:#111827;border:1px solid #1f2937;border-radius:20px;padding:32px;box-shadow:0 20px 25px -5px rgba(0,0,0,0.3);">
            <h1 style="margin-top:0;color:#f87171;font-size:32px;">🔒 Blocked during focus</h1>
            <p style="font-size:16px;line-height:1.6;color:#cbd5e1;">${reason}</p>
            <p style="font-size:14px;color:#94a3b8;margin-top:24px;">This content is blocked by Study Lock to help you focus.</p>
          </div>
        </div>
      `;
      console.log("Content blocked by Study Lock:", reason);
    }
  });
}

/**
 * Initialize mutation observer for YouTube
 */
const observer = new MutationObserver(removeYouTubeDistractions);
observer.observe(document.documentElement, { childList: true, subtree: true });

// Initial cleanup
removeYouTubeDistractions();

// Send context for evaluation
sendContext();

// Periodic cleanup for YouTube
setInterval(() => {
  removeYouTubeDistractions();
}, 2000);
