/**
 * MCADV Dashboard – real-time polling (no WebSocket required).
 * Polls /api/health every 10 seconds and updates the UI.
 */

const BOT_URL = (window.BOT_URL || 'http://localhost:5000');
const POLL_INTERVAL_MS = 10000;

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function setStatus(healthy) {
  const badge = document.getElementById('bot-status');
  if (!badge) return;
  badge.textContent = healthy ? 'Online' : 'Offline';
  badge.className = 'status-badge ' + (healthy ? 'status-online' : 'status-offline');
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

async function checkHealth() {
  try {
    const resp = await fetch(BOT_URL + '/api/health', { cache: 'no-store' });
    const data = await resp.json();
    setStatus(data.status === 'healthy');
    return data;
  } catch {
    setStatus(false);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Dashboard page – update metric cards
// ---------------------------------------------------------------------------

function updateDashboard(health) {
  if (!health) return;

  const uptimeEl = document.getElementById('uptime');
  if (uptimeEl && health.uptime_seconds !== undefined) {
    uptimeEl.textContent = formatUptime(health.uptime_seconds);
  }
}

function formatUptime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

// ---------------------------------------------------------------------------
// Admin page
// ---------------------------------------------------------------------------

function initAdmin() {
  const healthBtn = document.getElementById('health-check-btn');
  if (healthBtn) {
    healthBtn.addEventListener('click', async () => {
      const data = await checkHealth();
      const output = document.getElementById('health-result');
      if (output) output.textContent = JSON.stringify(data, null, 2);
    });
  }

  const resetBtn = document.getElementById('reset-sessions-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (confirm('Reset ALL active sessions? This cannot be undone.')) {
        fetch(BOT_URL + '/api/reset_sessions', { method: 'POST' })
          .then(() => alert('Sessions reset.'))
          .catch(() => alert('Failed to reset sessions. Check server connection.'));
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Refresh button (sessions page)
// ---------------------------------------------------------------------------

function initRefreshButton() {
  const btn = document.getElementById('refresh-btn');
  if (btn) {
    btn.addEventListener('click', pollAll);
  }
}

// ---------------------------------------------------------------------------
// Main poll loop
// ---------------------------------------------------------------------------

async function pollAll() {
  const health = await checkHealth();
  updateDashboard(health);
}

document.addEventListener('DOMContentLoaded', () => {
  pollAll();
  initAdmin();
  initRefreshButton();
  setInterval(pollAll, POLL_INTERVAL_MS);
});
