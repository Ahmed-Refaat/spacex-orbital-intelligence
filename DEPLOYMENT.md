# 🚀 Deployment Guide - SpaceX Orbital Intelligence

## Production Deployment (Current)

**Live URL**: https://spacex.ericcesar.com

### Architecture

```
Internet (Port 443/80)
         ↓
    Nginx Reverse Proxy
    - SSL Termination (Let's Encrypt)
    - HTTP → HTTPS Redirect
         ↓
    ┌────────────────────┬──────────────────┐
    ↓                    ↓                  ↓
Frontend:3100      Backend:8000        WebSocket:8000
(React App)        (FastAPI)           (Real-time)
    ↓                    ↓
    └────────────────────┴──────────────┐
                                        ↓
                        ┌───────────────┴───────────────┐
                        ↓                               ↓
                   Redis:6379                      Postgres:5432
                (localhost only)                 (localhost only)
                (password-protected)             (password-protected)
```

### Security Features

✅ **All services behind Nginx**
- No direct public access to Docker containers
- Ports 8000, 3100 bound to 127.0.0.1 only

✅ **SSL/HTTPS Enabled**
- Let's Encrypt certificate
- Auto-renewal configured
- HSTS recommended (optional)

✅ **Database Security**
- Redis: Strong password authentication
- PostgreSQL: Strong password authentication
- No public port exposure

✅ **Rate Limiting**
- Backend: `slowapi` with 10 req/min on export endpoints
- Nginx: Can add additional rate limiting if needed

## Nginx Configuration

**Location**: `/etc/nginx/sites-available/spacex.ericcesar.com.conf`

### Routes

| Path | Target | Purpose |
|------|--------|---------|
| `/` | `localhost:3100` | React frontend |
| `/api/*` | `localhost:8000` | Backend REST API |
| `/docs` | `localhost:8000` | API documentation |
| `/ws/*` | `localhost:8000` | WebSocket (real-time) |
| `/health` | `localhost:8000` | Health check |

### SSL Certificate

- **Provider**: Let's Encrypt
- **Auto-renewal**: Enabled via certbot
- **Certificate Path**: `/etc/letsencrypt/live/spacex.ericcesar.com/`
- **Renewal Check**: `sudo certbot renew --dry-run`

## Docker Compose

### Port Bindings (Secure)

```yaml
backend:
  ports:
    - "127.0.0.1:8000:8000"  # Localhost only

frontend:
  ports:
    - "127.0.0.1:3100:3000"  # Localhost only

redis:
  # No ports exposed (internal network only)

postgres:
  # No ports exposed (internal network only)
```

### Environment Variables

See `.env.example` for configuration template.

**Required**:
- `REDIS_PASSWORD` - Strong password for Redis
- `POSTGRES_PASSWORD` - Strong password for PostgreSQL

**Optional**:
- `SPACETRACK_USERNAME` - Space-Track API credentials
- `SPACETRACK_PASSWORD` - Space-Track API credentials
- `SPACEX_API_KEY` - API key for protected endpoints

## Deployment Steps

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/e-cesar9/spacex-orbital-intelligence.git
cd spacex-orbital-intelligence

# 2. Configure environment
cp .env.example backend/.env
# Edit backend/.env with your passwords

# 3. Start services
docker compose up -d

# 4. Configure Nginx (if not already done)
sudo cp nginx/spacex.ericcesar.com.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/spacex.ericcesar.com.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 5. Obtain SSL certificate
sudo certbot --nginx -d spacex.ericcesar.com
```

### Updates

```bash
# 1. Pull latest changes
cd /home/clawd/prod/spacex-orbital
git pull

# 2. Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d

# 3. Verify
curl -s https://spacex.ericcesar.com/health
```

## Monitoring

### Health Checks

```bash
# Overall health
curl https://spacex.ericcesar.com/health

# Container status
docker compose ps

# Logs
docker compose logs -f backend
docker compose logs -f frontend
```

### SSL Certificate Expiry

```bash
# Check certificate expiration
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run
```

## Troubleshooting

### 502 Bad Gateway

**Cause**: Backend/frontend containers not accessible

**Fix**:
```bash
docker compose ps  # Check if containers are running
docker compose logs backend  # Check for errors
sudo systemctl status nginx  # Check Nginx status
```

### SSL Certificate Issues

**Cause**: Certificate expired or not found

**Fix**:
```bash
sudo certbot certificates  # Check status
sudo certbot renew  # Force renewal if needed
sudo systemctl reload nginx
```

### Database Connection Errors

**Cause**: Wrong credentials or services not running

**Fix**:
```bash
# Check .env passwords match docker-compose.yml
cat backend/.env
# Restart services
docker compose restart
```

## Performance Tuning

### Nginx (Optional)

```nginx
# Add to server block for better performance
gzip on;
gzip_types text/plain text/css application/json application/javascript;
client_max_body_size 10M;
```

### Docker (Optional)

```yaml
# Add resource limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

## Security Checklist

- [x] SSL/HTTPS enabled
- [x] HTTP → HTTPS redirect
- [x] Ports bound to localhost only
- [x] Redis password-protected
- [x] PostgreSQL password-protected
- [x] Rate limiting enabled
- [x] CORS configured
- [ ] Firewall rules (optional)
- [ ] Fail2ban (optional)
- [ ] API key enforcement (optional)

## Backup & Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker exec spacex-orbital-postgres pg_dump -U spacex spacex_orbital > backup.sql

# Restore
cat backup.sql | docker exec -i spacex-orbital-postgres psql -U spacex spacex_orbital
```

### Redis Backup

```bash
# Redis automatically saves to /data (persistent volume)
docker compose down
docker run --rm -v spacex-orbital_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz -C /data .
docker compose up -d
```

---

**Last Updated**: 2026-02-07 by James (Rico's FDE)
