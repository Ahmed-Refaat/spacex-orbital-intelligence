import http from 'k6/http';
import { check } from 'k6';

/**
 * Smoke Test - Fast CI/CD validation
 * 
 * Purpose: Quick sanity check that basic endpoints work under light load.
 * Duration: 30 seconds
 * Load: 10 concurrent users
 * 
 * Run in CI/CD on every PR to catch performance regressions early.
 */

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'http_req_duration': ['p(95)<1000'],  // More relaxed for CI/CD
    'http_req_failed': ['rate<0.01'],     // < 1% errors
    'checks': ['rate>0.95'],              // > 95% checks pass
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://spacex.ericcesar.com';

export default function () {
  // Test 1: Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health status 200': (r) => r.status === 200,
    'health response time < 100ms': (r) => r.timings.duration < 100,
  });
  
  // Test 2: Satellites endpoint
  const satellitesRes = http.get(`${BASE_URL}/api/v1/satellites?limit=10`);
  check(satellitesRes, {
    'satellites status 200': (r) => r.status === 200,
    'satellites response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  // Test 3: Positions endpoint (critical path)
  const positionsRes = http.get(`${BASE_URL}/api/v1/satellites/positions?limit=10`);
  check(positionsRes, {
    'positions status 200': (r) => r.status === 200,
    'positions response time < 1s': (r) => r.timings.duration < 1000,
  });
}

export function handleSummary(data) {
  const passed = data.metrics.checks.values.passes;
  const failed = data.metrics.checks.values.fails;
  const total = passed + failed;
  const passRate = (passed / total) * 100;
  
  console.log('\n========== SMOKE TEST RESULTS ==========');
  console.log(`Checks: ${passed}/${total} passed (${passRate.toFixed(1)}%)`);
  console.log(`p95 latency: ${data.metrics.http_req_duration.values.p95.toFixed(2)}ms`);
  console.log(`Error rate: ${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%`);
  
  if (passRate < 95 || data.metrics.http_req_failed.rate > 0.01) {
    console.log('❌ SMOKE TEST FAILED - Performance regression detected');
    console.log('========================================\n');
    return {
      'smoke-summary.json': JSON.stringify(data, null, 2),
      'stdout': '❌ Smoke test failed',
    };
  }
  
  console.log('✅ SMOKE TEST PASSED');
  console.log('========================================\n');
  
  return {
    'smoke-summary.json': JSON.stringify(data, null, 2),
  };
}
