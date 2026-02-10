# Load Testing

Performance testing under various load conditions.

## Tools

- **k6**: JavaScript-based, great for realistic scenarios
- **Locust**: Python-based, easy to write complex tests

## k6 Load Tests

### Install

```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Smoke Test (baseline)

```javascript
// smoke.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,           // 10 virtual users
  duration: '30s',   // 30 seconds
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],   // Error rate < 1%
  },
};

export default function () {
  // Health check
  let res = http.get('https://spacex.ericcesar.com/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'satellites loaded': (r) => JSON.parse(r.body).satellites_loaded > 0,
  });
  
  // API call
  res = http.get('https://spacex.ericcesar.com/api/v1/satellites/positions');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time OK': (r) => r.timings.duration < 1000,
  });
  
  sleep(1);
}
```

Run:
```bash
k6 run smoke.js
```

### Load Test (sustained)

```javascript
// load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Ramp up to 200
    { duration: '5m', target: 200 },  // Stay at 200
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(99)<2000'],  // 99% < 2s
    http_req_failed: ['rate<0.05'],     // Error rate < 5%
  },
};

export default function () {
  const res = http.get('https://spacex.ericcesar.com/api/v1/satellites/positions');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(Math.random() * 3 + 1);  // 1-4 seconds
}
```

### Stress Test (breaking point)

```javascript
// stress.js
export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },
    { duration: '5m', target: 400 },
    { duration: '2m', target: 500 },  // Find breaking point
    { duration: '5m', target: 0 },
  ],
};
```

### Spike Test (sudden traffic)

```javascript
// spike.js
export const options = {
  stages: [
    { duration: '10s', target: 100 },
    { duration: '1m', target: 2000 },  // Sudden spike
    { duration: '10s', target: 100 },
    { duration: '3m', target: 100 },
    { duration: '10s', target: 0 },
  ],
};
```

### WebSocket Test

```javascript
// websocket.js
import ws from 'k6/ws';
import { check } from 'k6';

export const options = {
  vus: 100,
  duration: '5m',
};

export default function () {
  const url = 'wss://spacex.ericcesar.com/ws/positions';
  
  const res = ws.connect(url, {}, function (socket) {
    socket.on('open', () => console.log('WebSocket opened'));
    
    socket.on('message', (data) => {
      const msg = JSON.parse(data);
      check(msg, {
        'message type is positions': (m) => m.type === 'positions',
        'has satellite data': (m) => m.data && m.data.length > 0,
      });
    });
    
    socket.on('close', () => console.log('WebSocket closed'));
    socket.on('error', (e) => console.log('WebSocket error:', e));
    
    // Keep connection open for 30s
    socket.setTimeout(() => {
      socket.close();
    }, 30000);
  });
}
```

## Locust Load Tests

```python
# locustfile.py
from locust import HttpUser, task, between

class SpaceXUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3s between tasks
    
    @task(5)  # Weight: 5 (more frequent)
    def get_positions(self):
        """Get satellite positions."""
        self.client.get("/api/v1/satellites/positions")
    
    @task(2)
    def get_satellite_detail(self):
        """Get specific satellite."""
        self.client.get("/api/v1/satellites/44000")
    
    @task(1)
    def get_launches(self):
        """Get launches."""
        self.client.get("/api/v1/launches?limit=20")
    
    def on_start(self):
        """On user start."""
        # Check health
        response = self.client.get("/health")
        assert response.status_code == 200
```

Run:
```bash
locust -f locustfile.py --host=https://spacex.ericcesar.com

# Headless mode (no web UI)
locust -f locustfile.py --host=https://spacex.ericcesar.com \
  --users 100 --spawn-rate 10 --run-time 5m --headless
```

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| **API Response Time (p95)** | < 500ms | ??? |
| **API Response Time (p99)** | < 2s | ??? |
| **Error Rate** | < 0.1% | ??? |
| **Throughput** | 500 req/s | ??? |
| **WebSocket Connections** | 1000 concurrent | ??? |
| **TLE Update Time** | < 30s | ✅ 30s |

## Monitoring During Load Tests

Watch these metrics in Grafana/Prometheus:
```
- http_requests_total
- http_request_duration_seconds
- websocket_connections_total
- satellites_loaded
- cache_hits_total
- memory_usage_bytes
- cpu_usage_percent
```

## Infrastructure Scaling

### Horizontal Scaling

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3  # 3 backend instances
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Vertical Scaling

Increase resources per instance:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
```

## Results Analysis

After load test, check:
1. **Response time degradation** - should be linear, not exponential
2. **Error rate spike** - indicates breaking point
3. **Memory leaks** - memory should stabilize
4. **CPU usage** - should not hit 100% for long
5. **Cache efficiency** - hit rate should be >80%

## Safety Checklist

Before running load tests:
- [ ] Use staging environment (not production)
- [ ] Monitoring enabled (Grafana/Prometheus)
- [ ] Rate limiting configured
- [ ] Circuit breakers enabled
- [ ] Database connection pools sized
- [ ] Redis connection limits set
- [ ] Team notified

## Expected Bottlenecks

1. **TLE propagation** - CPU-intensive SGP4 calculations
2. **WebSocket broadcast** - Memory for 1000+ connections
3. **Database connections** - Pool exhaustion
4. **External API rate limits** - Celestrak, N2YO quotas

## Optimization Ideas

If bottlenecks found:
- Cache TLE propagation results (5-10 min TTL)
- WebSocket delta updates (send only changes)
- Database read replicas
- CDN for static assets
- Redis cluster mode
