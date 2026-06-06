import test from 'node:test';
import assert from 'node:assert';

const API_URL = 'http://localhost:5000/api';

test('Integration Test Suite - Premium Internship API', async (t) => {
  
  await t.test('GET /live - Liveness check should be UP', async () => {
    const res = await fetch(`${API_URL}/live`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.status, 'UP');
  });

  await t.test('GET /ready - Readiness check should be UP', async () => {
    const res = await fetch(`${API_URL}/ready`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.status, 'UP');
  });

  await t.test('GET /internships - Fetch default listings', async () => {
    const res = await fetch(`${API_URL}/internships`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.ok(Array.isArray(data.internships));
    assert.ok(typeof data.total === 'number');
  });

  await t.test('GET /filters - Fetch unique filters', async () => {
    const res = await fetch(`${API_URL}/filters`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.ok(Array.isArray(data.locations));
    assert.ok(Array.isArray(data.sources));
    assert.ok(Array.isArray(data.skills));
  });

  await t.test('GET /stats - Fetch statistics', async () => {
    const res = await fetch(`${API_URL}/stats`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.ok(data.metrics);
    assert.ok(data.charts);
    assert.ok(typeof data.metrics.totalScraped === 'number');
  });

  await t.test('POST /scrapers/run - Without admin key should return 401 Unauthorized', async () => {
    const res = await fetch(`${API_URL}/scrapers/run`, { method: 'POST' });
    assert.strictEqual(res.status, 401);
    const data = await res.json();
    assert.ok(data.error.includes('Unauthorized'));
  });

  await t.test('POST /scrapers/run - With admin key should queue successfully or fail fast if Redis is offline', async () => {
    const adminKey = process.env.ADMIN_API_KEY || 'super-secret-admin-key';
    const res = await fetch(`${API_URL}/scrapers/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-API-Key': adminKey
      }
    });
    // Should succeed (200), report already running (400), or fail fast if Redis is offline (503)
    assert.ok(res.status === 200 || res.status === 400 || res.status === 503);
    const data = await res.json();
    if (res.status === 200) {
      assert.ok(data.status === 'running');
    } else if (res.status === 503) {
      assert.ok(data.error.includes('offline'));
    }
  });

});
