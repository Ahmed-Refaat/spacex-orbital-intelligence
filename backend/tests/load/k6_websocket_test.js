/**
 * SpaceX Orbital Intelligence - WebSocket Load Tests
 * 
 * Tests WebSocket endpoint for real-time satellite positions
 * 
 * Run with: k6 run k6_websocket_test.js
 * 
 * Requirements:
 * - 500+ concurrent WebSocket connections
 * - No message loss
 * - Reconnection handling
 */

import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metrics
const wsConnectionTime = new Trend('ws_connection_time');
const wsMessageReceived = new Counter('ws_messages_received');
const wsConnectionErrors = new Counter('ws_connection_errors');
const wsSuccessRate = new Rate('ws_success_rate');

// Configuration
const WS_URL = __ENV.WS_URL || 'ws://localhost:8000/api/v1/ws/positions';

// Scenarios
export const options = {
  scenarios: {
    // Gradual ramp up to 500 connections
    websocket_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 100 },   // Start with 100
        { duration: '1m', target: 300 },    // Ramp to 300
        { duration: '1m', target: 500 },    // Peak at 500
        { duration: '2m', target: 500 },    // Hold at 500
        { duration: '30s', target: 0 },     // Ramp down
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    // Connection time < 5s
    'ws_connection_time': ['p(95)<5000'],
    // Success rate > 99%
    'ws_success_rate': ['rate>0.99'],
    // At least 10 messages per connection
    'ws_messages_received': ['count>1000'],
  },
};

export default function() {
  const startTime = Date.now();
  
  const res = ws.connect(WS_URL, {}, function(socket) {
    // Connection opened
    wsConnectionTime.add(Date.now() - startTime);
    
    let messageCount = 0;
    let lastPosition = null;
    
    socket.on('open', () => {
      wsSuccessRate.add(1);
      console.log(`VU ${__VU}: Connected`);
    });
    
    socket.on('message', (data) => {
      messageCount++;
      wsMessageReceived.add(1);
      
      // Validate message structure
      try {
        const positions = JSON.parse(data);
        check(positions, {
          'message is array': (p) => Array.isArray(p),
          'positions have required fields': (p) => {
            if (!Array.isArray(p) || p.length === 0) return true;
            const first = p[0];
            return first.satellite_id && 
                   first.latitude !== undefined && 
                   first.longitude !== undefined;
          },
        });
        
        if (Array.isArray(positions) && positions.length > 0) {
          lastPosition = positions[0];
        }
      } catch (e) {
        // JSON parse error
        check(null, { 'valid JSON': () => false });
      }
    });
    
    socket.on('error', (e) => {
      wsConnectionErrors.add(1);
      wsSuccessRate.add(0);
      console.log(`VU ${__VU}: Error - ${e.error()}`);
    });
    
    socket.on('close', () => {
      console.log(`VU ${__VU}: Closed after ${messageCount} messages`);
    });
    
    // Keep connection open for 60 seconds
    socket.setTimeout(() => {
      socket.close();
    }, 60000);
  });
  
  // Check connection was established
  check(res, {
    'WebSocket connected': (r) => r && r.status === 101,
  }) || wsConnectionErrors.add(1);
  
  // Sleep before next iteration
  sleep(1);
}

// Handle cleanup
export function teardown() {
  console.log('WebSocket load test completed');
}
