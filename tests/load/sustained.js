import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const positionsLatency = new Trend('positions_latency');
const simulationLatency = new Trend('simulation_latency');

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Warmup
    { duration: '2m', target: 200 },   // Ramp-up to 200 concurrent users
    { duration: '5m', target: 200 },   // Sustained load
    { duration: '30s', target: 0 },    // Ramp-down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'],      // p95 < 500ms
    'http_req_failed': ['rate<0.01'],        // < 1% errors
    'errors': ['rate<0.01'],                 // < 1% business logic errors
    'positions_latency': ['p(95)<500'],      // Positions endpoint p95 < 500ms
    'simulation_latency': ['p(95)<2000'],    // Simulation endpoint p95 < 2s (CPU-intensive)
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://spacex.ericcesar.com';

export default function () {
  // Test 1: Health check (lightweight)
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health status 200': (r) => r.status === 200,
    'health has satellites_loaded': (r) => {
      try {
        return JSON.parse(r.body).satellites_loaded !== undefined;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(healthRes.status !== 200);
  
  // Test 2: List satellites (common operation)
  const satellitesRes = http.get(`${BASE_URL}/api/v1/satellites?limit=100`);
  check(satellitesRes, {
    'satellites status 200': (r) => r.status === 200,
    'satellites has data': (r) => {
      try {
        return JSON.parse(r.body).satellites?.length > 0;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(satellitesRes.status !== 200);
  
  // Test 3: Get positions (CRITICAL endpoint - most CPU intensive)
  const positionsStart = Date.now();
  const positionsRes = http.get(`${BASE_URL}/api/v1/satellites/positions?limit=50`);
  const positionsDuration = Date.now() - positionsStart;
  
  positionsLatency.add(positionsDuration);
  
  check(positionsRes, {
    'positions status 200': (r) => r.status === 200,
    'positions latency < 500ms': () => positionsDuration < 500,
    'positions has data': (r) => {
      try {
        return JSON.parse(r.body).positions?.length > 0;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(positionsRes.status !== 200);
  
  // Test 4: Analytics constellation overview
  const analyticsRes = http.get(`${BASE_URL}/api/v1/analytics/constellation-overview`);
  check(analyticsRes, {
    'analytics status 200': (r) => r.status === 200,
  });
  errorRate.add(analyticsRes.status !== 200);
  
  // Test 5: Monte Carlo simulation (10% of users, very CPU-intensive)
  if (Math.random() < 0.1) {
    const simulationStart = Date.now();
    const simulationRes = http.post(
      `${BASE_URL}/api/v1/simulation/launch`,
      JSON.stringify({
        thrust_N: 8000000,
        thrust_variance: 0.05,
        Isp: 360,
        n_runs: 100  // Small run for load testing
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
    const simulationDuration = Date.now() - simulationStart;
    
    simulationLatency.add(simulationDuration);
    
    check(simulationRes, {
      'simulation status 200': (r) => r.status === 200,
      'simulation completes': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.status === 'complete' || body.status === 'running';
        } catch {
          return false;
        }
      },
    });
    errorRate.add(simulationRes.status !== 200);
  }
  
  // Think time (simulate real user)
  sleep(1);
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data, null, 2),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  const checks = data.metrics.checks || {};
  const httpReqDuration = data.metrics.http_req_duration || {};
  const httpReqs = data.metrics.http_reqs || {};
  const errors = data.metrics.errors || {};
  const positionsLatency = data.metrics.positions_latency || {};
  const simulationLatency = data.metrics.simulation_latency || {};
  
  let summary = `

${indent}========== LOAD TEST RESULTS ==========

${indent}✓ Checks........................: ${checks.passes || 0}/${(checks.passes || 0) + (checks.fails || 0)} passed
${indent}  HTTP Request Duration:
${indent}    - p50........................: ${httpReqDuration.values?.p50?.toFixed(2) || 'N/A'} ms
${indent}    - p95........................: ${httpReqDuration.values?.p95?.toFixed(2) || 'N/A'} ms
${indent}    - p99........................: ${httpReqDuration.values?.p99?.toFixed(2) || 'N/A'} ms
${indent}    - max........................: ${httpReqDuration.values?.max?.toFixed(2) || 'N/A'} ms
${indent}  
${indent}  Throughput....................: ${httpReqs.rate?.toFixed(2) || 'N/A'} req/s
${indent}  Total Requests................: ${httpReqs.count || 0}
${indent}  
${indent}  Error Rate....................: ${((errors.rate || 0) * 100).toFixed(2)}%
${indent}  
${indent}  Positions Endpoint:
${indent}    - p50........................: ${positionsLatency.values?.p50?.toFixed(2) || 'N/A'} ms
${indent}    - p95........................: ${positionsLatency.values?.p95?.toFixed(2) || 'N/A'} ms
${indent}  
${indent}  Simulation Endpoint:
${indent}    - p50........................: ${simulationLatency.values?.p50?.toFixed(2) || 'N/A'} ms
${indent}    - p95........................: ${simulationLatency.values?.p95?.toFixed(2) || 'N/A'} ms

${indent}======================================
`;
  
  // Check thresholds
  const thresholdsFailed = [];
  if (httpReqDuration.values?.p95 > 500) {
    thresholdsFailed.push('❌ p95 latency > 500ms');
  }
  if ((errors.rate || 0) > 0.01) {
    thresholdsFailed.push('❌ Error rate > 1%');
  }
  if (positionsLatency.values?.p95 > 500) {
    thresholdsFailed.push('❌ Positions p95 > 500ms');
  }
  
  if (thresholdsFailed.length > 0) {
    summary += `\n${indent}⚠️  THRESHOLDS FAILED:\n`;
    thresholdsFailed.forEach(failure => {
      summary += `${indent}${failure}\n`;
    });
  } else {
    summary += `\n${indent}✅ All thresholds passed!\n`;
  }
  
  return summary;
}
