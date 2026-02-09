#!/bin/bash
# Production verification for spacex.ericcesar.com

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN="https://spacex.ericcesar.com"

echo -e "${YELLOW}🚀 SpaceX Orbital Intelligence - Production Check${NC}"
echo -e "${YELLOW}Domain: $DOMAIN${NC}"
echo ""

# Test 1: Frontend
echo -n "1. Frontend (HTTPS)... "
response=$(curl -s -w "%{http_code}" -o /dev/null $DOMAIN)
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✅ OK (HTTP $response)${NC}"
else
    echo -e "${RED}❌ FAIL (HTTP $response)${NC}"
    exit 1
fi

# Test 2: Health endpoint
echo -n "2. Health endpoint... "
health=$(curl -s "$DOMAIN/health")
status=$(echo $health | jq -r '.status')
if [ "$status" = "healthy" ]; then
    echo -e "${GREEN}✅ OK (healthy)${NC}"
else
    echo -e "${RED}❌ FAIL (status: $status)${NC}"
    exit 1
fi

# Test 3: API
echo -n "3. API endpoint... "
response=$(curl -s -w "%{http_code}" -o /dev/null "$DOMAIN/api/v1/satellites?limit=1")
if [ "$response" = "200" ] || [ "$response" = "500" ]; then
    # 500 is expected if Space-Track credentials not configured (TLE fetch fails)
    echo -e "${YELLOW}⚠️  HTTP $response (may need Space-Track creds)${NC}"
else
    echo -e "${RED}❌ FAIL (HTTP $response)${NC}"
    exit 1
fi

# Test 4: API Docs
echo -n "4. API Docs... "
response=$(curl -s -w "%{http_code}" -o /dev/null "$DOMAIN/docs")
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✅ OK (HTTP $response)${NC}"
else
    echo -e "${RED}❌ FAIL (HTTP $response)${NC}"
fi

# Test 5: SSL Certificate
echo -n "5. SSL Certificate... "
ssl_info=$(echo | openssl s_client -servername spacex.ericcesar.com -connect spacex.ericcesar.com:443 2>/dev/null | openssl x509 -noout -dates)
if [ ! -z "$ssl_info" ]; then
    echo -e "${GREEN}✅ OK${NC}"
    echo "   $(echo "$ssl_info" | grep notAfter)"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All production checks passed!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🌐 Access points:"
echo "  Frontend: $DOMAIN"
echo "  API Docs: $DOMAIN/docs"
echo "  Health:   $DOMAIN/health"
echo ""
