# Load Testing - SpaceX Orbital Intelligence

## Prerequisites

```bash
# Install k6
snap install k6

# Or via apt
curl -sS https://dl.k6.io/key.gpg | sudo apt-key add -
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt update && sudo apt install k6
```

## Running Tests

### API Load Tests

```bash
# Smoke test (1 VU, 30s) - Quick validation
k6 run -e SCENARIO=smoke k6_load_test.js

# Load test (50 VUs, 5min) - Normal production load
k6 run -e SCENARIO=load k6_load_test.js

# Stress test (200 VUs, 2min) - Find breaking point
k6 run -e SCENARIO=stress k6_load_test.js

# Spike test (0→300→0 VUs) - Traffic bursts
k6 run -e SCENARIO=spike k6_load_test.js

# Soak test (50 VUs, 10min) - Memory leaks, degradation
k6 run -e SCENARIO=soak k6_load_test.js
```

### WebSocket Load Tests

```bash
# Test 500 concurrent WebSocket connections
k6 run k6_websocket_test.js
```

### Custom Configuration

```bash
# Custom base URL
k6 run -e BASE_URL=https://api.example.com k6_load_test.js

# With API key
k6 run -e API_KEY=your-key-here k6_load_test.js

# Custom WebSocket URL
k6 run -e WS_URL=wss://api.example.com/ws k6_websocket_test.js
```

## Thresholds (SLOs)

| Metric | Threshold | Description |
|--------|-----------|-------------|
| `http_req_duration p(95)` | < 500ms | 95th percentile response time |
| `http_req_duration p(99)` | < 1000ms | 99th percentile response time |
| `http_req_failed` | < 1% | Error rate |
| `propagation_duration p(95)` | < 200ms | Satellite propagation speed |
| `risk_calculation_duration p(95)` | < 1000ms | Risk analysis speed |
| `ws_connection_time p(95)` | < 5000ms | WebSocket connection time |
| `ws_success_rate` | > 99% | WebSocket reliability |

## Output Formats

```bash
# JSON output
k6 run --out json=results.json k6_load_test.js

# InfluxDB (for Grafana)
k6 run --out influxdb=http://localhost:8086/k6 k6_load_test.js

# Cloud (k6 Cloud)
k6 cloud k6_load_test.js
```

## Interpreting Results

### Good Results ✅
```
✓ http_req_duration..............: avg=45.23ms  p(95)=120.5ms
✓ http_req_failed................: 0.00%
✓ iterations.....................: 5000
```

### Bad Results ❌
```
✗ http_req_duration..............: avg=850.23ms p(95)=2500ms
✗ http_req_failed................: 5.23%
```

## Recommended Test Order

1. **Smoke test** - Verify basic functionality
2. **Load test** - Establish baseline
3. **Stress test** - Find limits
4. **Spike test** - Test recovery
5. **Soak test** - Check for leaks

## CI/CD Integration

```yaml
# GitHub Actions example
load-test:
  runs-on: ubuntu-latest
  steps:
    - uses: grafana/k6-action@v0.3.1
      with:
        filename: tests/load/k6_load_test.js
        flags: -e SCENARIO=load -e BASE_URL=${{ secrets.API_URL }}
```
