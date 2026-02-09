/**
 * SpaceX Orbital Intelligence - Load Tests
 * 
 * Run with: k6 run k6_load_test.js
 * 
 * Tests:
 * 1. Smoke test: 1 VU, 30s - Basic functionality
 * 2. Load test: 50 VUs, 5m - Normal load
 * 3. Stress test: 200 VUs, 2m - High load
 * 4. Spike test: 0→300→0 VUs - Traffic spikes
 * 5. Soak test: 50 VUs, 10m - Sustained load (check for memory leaks)
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metrics
const apiErrors = new Counter('api_errors');
const propagationDuration = new Trend('propagation_duration');
const riskCalculationDuration = new Trend('risk_calculation_duration');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || '';

// Test scenarios - run specific scenario with: k6 run -e SCENARIO=load k6_load_test.js
const scenarios = {
  smoke: {
    executor: 'constant-vus',
    vus: 1,
    duration: '30s',
  },
  load: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '30s', target: 20 },  // Ramp up
      { duration: '3m', target: 50 },   // Steady state
      { duration: '30s', target: 0 },   // Ramp down
    ],
  },
  stress: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '30s', target: 100 },
      { duration: '1m', target: 200 },
      { duration: '30s', target: 0 },
    ],
  },
  spike: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '10s', target: 300 },  // Sudden spike
      { duration: '30s', target: 300 },  // Hold
      { duration: '10s', target: 0 },    // Drop
    ],
  },
  soak: {
    executor: 'constant-vus',
    vus: 50,
    duration: '10m',
  },
};

// Select scenario from env var or default to smoke
const selectedScenario = __ENV.SCENARIO || 'smoke';
export const options = {
  scenarios: {
    default: scenarios[selectedScenario] || scenarios.smoke,
  },
  thresholds: {
    // p95 response time must be < 500ms
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    // Error rate must be < 1%
    'http_req_failed': ['rate<0.01'],
    // Custom thresholds
    'propagation_duration': ['p(95)<200'],
    'risk_calculation_duration': ['p(95)<1000'],
  },
};

// Headers
function getHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  return headers;
}

// Main test function
export default function() {
  const headers = getHeaders();
  
  group('Health Check', () => {
    const res = http.get(`${BASE_URL}/health`, { headers });
    check(res, {
      'health status is 200': (r) => r.status === 200,
      'health response < 100ms': (r) => r.timings.duration < 100,
    }) || apiErrors.add(1);
  });
  
  group('Get All Positions', () => {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/satellites/positions`, { headers });
    propagationDuration.add(Date.now() - start);
    
    check(res, {
      'positions status is 200': (r) => r.status === 200,
      'positions has data': (r) => {
        const body = r.json();
        return body && body.positions && body.positions.length > 0;
      },
      'positions response < 500ms': (r) => r.timings.duration < 500,
    }) || apiErrors.add(1);
  });
  
  group('Get Satellites List', () => {
    const res = http.get(`${BASE_URL}/api/v1/satellites?limit=100`, { headers });
    check(res, {
      'satellites list status is 200': (r) => r.status === 200,
      'satellites list response < 300ms': (r) => r.timings.duration < 300,
    }) || apiErrors.add(1);
  });
  
  group('Get Single Satellite', () => {
    // Use ISS as known satellite
    const res = http.get(`${BASE_URL}/api/v1/satellites/25544`, { headers });
    check(res, {
      'single satellite status is 200 or 404': (r) => r.status === 200 || r.status === 404,
    });
  });
  
  group('Density Analysis', () => {
    const res = http.get(`${BASE_URL}/api/v1/analysis/density?altitude_km=550&tolerance_km=50`, { headers });
    check(res, {
      'density status is 200': (r) => r.status === 200,
      'density response < 1s': (r) => r.timings.duration < 1000,
    }) || apiErrors.add(1);
  });
  
  group('Risk Analysis (CPU-intensive)', () => {
    // This is O(n²) - test with shorter time window
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/analysis/risk/25544?hours_ahead=1`, { headers });
    riskCalculationDuration.add(Date.now() - start);
    
    check(res, {
      'risk status is 200 or 404': (r) => r.status === 200 || r.status === 404,
      'risk response < 2s': (r) => r.timings.duration < 2000,
    });
  });
  
  group('Hotspots', () => {
    const res = http.get(`${BASE_URL}/api/v1/analysis/hotspots`, { headers });
    check(res, {
      'hotspots status is 200': (r) => r.status === 200,
    }) || apiErrors.add(1);
  });
  
  group('Constellation Health', () => {
    const res = http.get(`${BASE_URL}/api/v1/analysis/constellation/health`, { headers });
    check(res, {
      'constellation health status is 200': (r) => r.status === 200,
    }) || apiErrors.add(1);
  });
  
  group('Launches', () => {
    const res = http.get(`${BASE_URL}/api/v1/launches?limit=10`, { headers });
    check(res, {
      'launches status is 200': (r) => r.status === 200,
    }) || apiErrors.add(1);
  });
  
  // Short sleep between iterations
  sleep(1);
}

// Lifecycle hooks
export function setup() {
  console.log(`Running ${selectedScenario} test against ${BASE_URL}`);
  
  // Verify API is up
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    throw new Error(`API not available: ${res.status}`);
  }
  
  return { startTime: Date.now() };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`Test completed in ${duration.toFixed(1)}s`);
}
