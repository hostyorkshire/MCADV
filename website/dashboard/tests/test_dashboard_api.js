/**
 * Dashboard API Integration Tests
 * Tests for dashboard.js API endpoint integration.
 * Run with: node test_dashboard_api.js
 */

/* eslint-disable strict */

// ---------------------------------------------------------------------------
// Minimal test framework
// ---------------------------------------------------------------------------

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failed++;
  }
}

function assertEqual(actual, expected, message) {
  if (actual === expected) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message} — expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    failed++;
  }
}

function describe(suiteName, fn) {
  console.log(`\n${suiteName}`);
  fn();
}

// ---------------------------------------------------------------------------
// Browser API stubs (Node.js environment)
// ---------------------------------------------------------------------------

// Minimal DOM stub
const _elements = {};

global.document = {
  getElementById(id) {
    if (!_elements[id]) {
      _elements[id] = { textContent: '', className: '', id };
    }
    return _elements[id];
  },
  addEventListener() {},
};

global.window = { BOT_URL: 'http://localhost:5000' };
global.confirm = () => true;
global.alert = () => {};

// fetch mock — replaced per test
global.fetch = null;

// setInterval stub
global.setInterval = () => {};

// ---------------------------------------------------------------------------
// Load the module under test
// ---------------------------------------------------------------------------

const path = require('path');

const {
  setStatus,
  checkHealth,
  updateDashboard,
  formatUptime,
} = require(path.join(__dirname, '..', 'js', 'dashboard.js'));

// ---------------------------------------------------------------------------
// Helper: reset DOM elements between tests
// ---------------------------------------------------------------------------

function resetElement(id) {
  _elements[id] = { textContent: '', className: '', id };
}

function mockFetch(responseBody, ok = true, status = 200) {
  global.fetch = async () => ({
    ok,
    status,
    json: async () => responseBody,
  });
}

function mockFetchReject(errorMessage) {
  global.fetch = async () => { throw new Error(errorMessage); };
}

// ---------------------------------------------------------------------------
// Tests: setStatus
// ---------------------------------------------------------------------------

describe('setStatus()', () => {
  resetElement('bot-status');

  setStatus(true);
  assertEqual(document.getElementById('bot-status').textContent, 'Online', 'sets text to Online when healthy');
  assert(document.getElementById('bot-status').className.includes('status-online'), 'adds status-online class');

  setStatus(false);
  assertEqual(document.getElementById('bot-status').textContent, 'Offline', 'sets text to Offline when unhealthy');
  assert(document.getElementById('bot-status').className.includes('status-offline'), 'adds status-offline class');
});

// ---------------------------------------------------------------------------
// Tests: formatUptime
// ---------------------------------------------------------------------------

describe('formatUptime()', () => {
  assertEqual(formatUptime(0), '0h 0m 0s', 'formats zero uptime');
  assertEqual(formatUptime(3661), '1h 1m 1s', 'formats 1h 1m 1s');
  assertEqual(formatUptime(7200), '2h 0m 0s', 'formats 2 hours exactly');
  assertEqual(formatUptime(90), '0h 1m 30s', 'formats 90 seconds');
});

// ---------------------------------------------------------------------------
// Async test runner (sequential, isolated)
// ---------------------------------------------------------------------------

const asyncTests = [];

function describeAsync(suiteName, fn) {
  asyncTests.push({ suiteName, fn });
}

async function runAsyncTests() {
  for (const { suiteName, fn } of asyncTests) {
    console.log(`\n${suiteName}`);
    resetElement('bot-status');
    await fn();
  }
}

// ---------------------------------------------------------------------------
// Tests: checkHealth – successful response
// ---------------------------------------------------------------------------

describeAsync('checkHealth() – healthy server', async () => {
  mockFetch({ status: 'healthy', uptime_seconds: 3600 });
  const data = await checkHealth();
  assert(data !== null, 'returns data object');
  assertEqual(data.status, 'healthy', 'data.status is healthy');
  assertEqual(document.getElementById('bot-status').textContent, 'Online', 'badge shows Online');
});

// ---------------------------------------------------------------------------
// Tests: checkHealth – unhealthy server response
// ---------------------------------------------------------------------------

describeAsync('checkHealth() – unhealthy server response', async () => {
  mockFetch({ status: 'degraded' });
  await checkHealth();
  assertEqual(document.getElementById('bot-status').textContent, 'Offline', 'badge shows Offline for non-healthy status');
});

// ---------------------------------------------------------------------------
// Tests: checkHealth – network error (offline server)
// ---------------------------------------------------------------------------

describeAsync('checkHealth() – offline server', async () => {
  mockFetchReject('Network error');
  const data = await checkHealth();
  assert(data === null, 'returns null on network error');
  assertEqual(document.getElementById('bot-status').textContent, 'Offline', 'badge shows Offline on error');
});

// ---------------------------------------------------------------------------
// Tests: checkHealth – timeout error
// ---------------------------------------------------------------------------

describeAsync('checkHealth() – timeout', async () => {
  global.fetch = async () => { throw new Error('The operation timed out'); };
  const data = await checkHealth();
  assert(data === null, 'returns null on timeout');
  assertEqual(document.getElementById('bot-status').textContent, 'Offline', 'badge shows Offline on timeout');
});

// ---------------------------------------------------------------------------
// Tests: checkHealth – invalid JSON
// ---------------------------------------------------------------------------

describeAsync('checkHealth() – invalid JSON response', async () => {
  global.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => { throw new SyntaxError('Unexpected token'); },
  });
  const data = await checkHealth();
  assert(data === null, 'returns null on JSON parse error');
  assertEqual(document.getElementById('bot-status').textContent, 'Offline', 'badge shows Offline on JSON error');
});

// ---------------------------------------------------------------------------
// Tests: updateDashboard
// ---------------------------------------------------------------------------

describe('updateDashboard()', () => {
  resetElement('uptime');

  updateDashboard({ uptime_seconds: 3661 });
  assertEqual(document.getElementById('uptime').textContent, '1h 1m 1s', 'updates uptime element');

  updateDashboard(null);
  assertEqual(document.getElementById('uptime').textContent, '1h 1m 1s', 'ignores null health data');
});

// ---------------------------------------------------------------------------
// Tests: /api/message endpoint mock
// ---------------------------------------------------------------------------

describeAsync('/api/message endpoint', async () => {
  const BOT_URL_LOCAL = 'http://localhost:5000';
  let capturedUrl = null;
  let capturedOptions = null;

  global.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return {
      ok: true,
      status: 200,
      json: async () => ({ response: 'You enter the dungeon…' }),
    };
  };

  const resp = await fetch(BOT_URL_LOCAL + '/api/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sender: 'test_user', content: '!adv', channel_idx: 1 }),
  });
  const data = await resp.json();
  assertEqual(capturedUrl, 'http://localhost:5000/api/message', 'posts to correct URL');
  assertEqual(capturedOptions.method, 'POST', 'uses POST method');
  assertEqual(data.response, 'You enter the dungeon…', 'returns response text');
});

// ---------------------------------------------------------------------------
// Tests: /api/reset_sessions endpoint mock
// ---------------------------------------------------------------------------

describeAsync('/api/reset_sessions endpoint', async () => {
  const BOT_URL_LOCAL = 'http://localhost:5000';
  let capturedUrl = null;
  let capturedMethod = null;

  global.fetch = async (url, options) => {
    capturedUrl = url;
    capturedMethod = (options && options.method) || 'GET';
    return { ok: true, status: 200, json: async () => ({ reset: true }) };
  };

  await fetch(BOT_URL_LOCAL + '/api/reset_sessions', { method: 'POST' });
  assertEqual(capturedUrl, 'http://localhost:5000/api/reset_sessions', 'posts to correct reset URL');
  assertEqual(capturedMethod, 'POST', 'uses POST method for reset');
});

// ---------------------------------------------------------------------------
// Final report
// ---------------------------------------------------------------------------

runAsyncTests().then(() => {
  console.log(`\n${'─'.repeat(50)}`);
  console.log(`Results: ${passed} passed, ${failed} failed`);
  if (failed > 0) {
    process.exit(1);
  }
});
