# 🚀 SETUP GUIDE - SpaceX Orbital Intelligence

## Quick Start (5 minutes)

### Prerequisites

- Docker & Docker Compose
- Git
- (Optional) Space-Track.org account

### 1. Clone & Configure

```bash
# Clone the repository
git clone https://github.com/e-cesar9/spacex-orbital-intelligence.git
cd spacex-orbital-intelligence

# Copy environment template
cp backend/.env.example backend/.env

# Generate secure passwords
python3 -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(32))" >> backend/.env
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))" >> backend/.env
python3 -c "import secrets; print('SPACEX_API_KEY=' + secrets.token_urlsafe(32))" >> backend/.env

# Edit backend/.env and add your Space-Track credentials
nano backend/.env
```

### 2. Launch

```bash
# Build and start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 3. Access

- **Frontend:** http://localhost:3100
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## 🔒 Security Setup (CRITICAL)

### File Permissions

```bash
# Secure .env file (owner read/write only)
chmod 600 backend/.env
chmod 700 backend/

# Verify
ls -la backend/.env
# Should show: -rw------- (600)
```

### Verify No Secrets in Git

```bash
# Check what's tracked
git ls-files | grep -iE "\.env$|secret|credential"

# Should return ONLY:
# .secrets.baseline
# backend/app/core/secrets.py
# (NO .env files!)

# If .env appears, something is wrong:
git rm --cached backend/.env
echo "backend/.env" >> .gitignore
```

### API Key Configuration

```bash
# Your API key is in backend/.env
cat backend/.env | grep SPACEX_API_KEY

# Test API with key:
curl -H "X-API-Key: YOUR_KEY_HERE" http://localhost:8000/api/v1/satellites
```

---

## 🛠️ Development Setup

### With Virtual Environment

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Full test suite
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## 🌐 Production Deployment

### Prerequisites

- VPS or cloud instance (2GB+ RAM)
- Domain name
- SSL certificate (Let's Encrypt)

### 1. Environment Variables

```bash
# On production server, set environment variables:
export REDIS_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export POSTGRES_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export SPACEX_API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Space-Track credentials
export SPACETRACK_USERNAME="your_email@example.com"
export SPACETRACK_PASSWORD="your_password"

# CORS
export CORS_ORIGINS="https://yourdomain.com"

# Environment
export ENV="production"
```

### 2. Nginx Configuration

```nginx
# /etc/nginx/sites-available/spacex.yourdomain.com

server {
    server_name spacex.yourdomain.com;
    
    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
    
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/spacex.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/spacex.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = spacex.yourdomain.com) {
        return 301 https://$host$request_uri;
    }
    
    server_name spacex.yourdomain.com;
    listen 80;
    return 404;
}
```

### 3. SSL Certificate

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d spacex.yourdomain.com

# Auto-renewal (already set up by certbot)
sudo certbot renew --dry-run
```

### 4. Deploy

```bash
# Pull latest
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d

# Check logs
docker compose logs -f

# Verify health
curl https://spacex.yourdomain.com/health
```

---

## 📊 Monitoring

### Prometheus + Grafana (Optional)

```bash
# Add to docker-compose.yml
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3000
# Default: admin/admin
```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend

# With timestamps
docker compose logs -f --timestamps

# Last 100 lines
docker compose logs --tail=100
```

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Service status
docker compose ps

# Container stats
docker stats
```

---

## 🔧 Troubleshooting

### "REDIS_PASSWORD not set" Error

```bash
# Make sure backend/.env exists and contains:
cat backend/.env | grep REDIS_PASSWORD

# If missing, regenerate:
python3 -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(32))" >> backend/.env
```

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8000
sudo lsof -i :3100

# Kill the process or change ports in docker-compose.yml
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Reset database
docker compose down -v
docker compose up -d
```

### TLE Data Not Loading

```bash
# Check backend logs
docker compose logs backend | grep TLE

# Manual update
docker compose exec backend python -c "from app.services.tle_service import tle_service; import asyncio; asyncio.run(tle_service.update_orbital_engine())"
```

---

## 📚 Documentation

- **API Docs:** `/docs` (Swagger UI)
- **Security:** `SECURITY_PUBLIC_REPO.md`
- **Security Audit:** `SECURITY_AUDIT_REPORT.md`
- **Business Evaluation:** `BUSINESS_EVALUATION_REPORT.md`
- **Architecture:** `README.md`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**⚠️ NEVER commit secrets!** See `SECURITY_PUBLIC_REPO.md`

---

## 📞 Support

- **Issues:** https://github.com/e-cesar9/spacex-orbital-intelligence/issues
- **Discussions:** https://github.com/e-cesar9/spacex-orbital-intelligence/discussions
- **Email:** [Your email]

---

## 📜 License

[Your License]

---

**Happy Orbital Intelligence! 🛰️**
