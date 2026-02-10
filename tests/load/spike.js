import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 100 },   // Normal load baseline
    { duration: '30s', target: 1000 },  // Spike to 10x (stress test)
    { duration: '1m', target: 1000 },   // Hold spike
    { duration: '30s', target: 100 },   // Return to normal
    { duration: '2m', target: 100 },    // Recovery observation period
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000'],  // Relaxed during spike
    'http_req_failed': ['rate<0.05'],     // Allow 5% errors during spike
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://spacex.ericcesar.com';

export default function () {
  // Focus on main endpoints during spike
  const res = http.get(`${BASE_URL}/api/v1/satellites?limit=50`);
  
  check(res, {
    'status 200 or 429 or 503': (r) => [200, 429, 503].includes(r.status),
  });
  
  sleep(0.1); // Faster requests during spike
}

export function handleSummary(data) {
  console.log('\n========== SPIKE TEST RESULTS ==========');
  console.log(`Max VUs: 1000`);
  console.log(`p95 latency: ${data.metrics.http_req_duration.values.p95.toFixed(2)}ms`);
  console.log(`Error rate: ${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%`);
  console.log(`Total requests: ${data.metrics.http_reqs.count}`);
  console.log('========================================\n');
  
  return {
    'spike-summary.json': JSON.stringify(data, null, 2),
  };
}
