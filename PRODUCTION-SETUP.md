# 🚀 Production Setup - spacex.ericcesar.com

**Status:** ✅ **DÉPLOYÉ ET OPÉRATIONNEL**

## ✅ Ce qui fonctionne

- ✅ HTTPS (SSL Let's Encrypt)
- ✅ Frontend: https://spacex.ericcesar.com/
- ✅ Backend API: https://spacex.ericcesar.com/api/
- ✅ API Docs: https://spacex.ericcesar.com/docs
- ✅ WebSocket: wss://spacex.ericcesar.com/ws
- ✅ Health check: https://spacex.ericcesar.com/health
- ✅ Nginx reverse proxy configuré
- ✅ Docker containers running

## ⚠️ Configuration Requise (Optionnel)

### Space-Track.org Credentials

Pour charger des TLE (Two-Line Elements) satellites depuis Space-Track:

1. **Créer un compte gratuit:** https://www.space-track.org/auth/createAccount
2. **Ajouter les credentials au fichier `.env`:**

```bash
cd /home/clawd/prod/spacex-orbital-intelligence/backend

# Ajouter à .env
echo "SPACE_TRACK_USERNAME=ton_username" >> .env
echo "SPACE_TRACK_PASSWORD=ton_password" >> .env
```

3. **Redémarrer le backend:**
```bash
cd /home/clawd/prod/spacex-orbital-intelligence
docker compose restart backend
```

**Sans ces credentials:** L'API fonctionne mais retourne 0 satellites.

---

## 🔧 Commandes de Gestion

### Vérifier le Status
```bash
cd /home/clawd/prod/spacex-orbital-intelligence

# Quick check
./verify-prod.sh

# Containers status
docker compose ps

# Logs
docker compose logs -f backend
docker compose logs -f frontend
```

### Redémarrer les Services
```bash
cd /home/clawd/prod/spacex-orbital-intelligence

# Redémarrer tout
docker compose restart

# Redémarrer un service spécifique
docker compose restart backend
docker compose restart frontend
```

### Rebuild (après changements code)
```bash
cd /home/clawd/prod/spacex-orbital-intelligence

# Pull latest code
git pull

# Rebuild et redémarrer
docker compose down
docker compose up -d --build

# Vérifier
./verify-prod.sh
```

### Nginx
```bash
# Test config
sudo nginx -t

# Reload (sans downtime)
sudo systemctl reload nginx

# Restart (avec downtime)
sudo systemctl restart nginx

# Logs
sudo tail -f /var/log/nginx/error.log
```

---

## 📊 Monitoring

### Health Check
```bash
curl https://spacex.ericcesar.com/health | jq
```

**Output attendu:**
```json
{
  "status": "healthy",
  "satellites_loaded": 0,
  "cache_connected": true,
  "last_tle_update": null
}
```

### Logs en Temps Réel
```bash
# Backend
docker logs -f spacex-orbital-backend

# Frontend
docker logs -f spacex-orbital-frontend

# All
docker compose logs -f
```

### Système
```bash
# Docker status
docker ps

# Disk usage
df -h

# Memory
free -h

# Processes
htop
```

---

## 🔐 Sécurité

### Certificats SSL
- **Provider:** Let's Encrypt
- **Auto-renewal:** Géré par Certbot
- **Vérifier expiration:**
```bash
sudo certbot certificates
```

### Renouveler manuellement (si besoin)
```bash
sudo certbot renew --dry-run  # Test
sudo certbot renew           # Réel
sudo systemctl reload nginx  # Reload config
```

### Ports Exposés
- `80` → Redirige vers HTTPS (443)
- `443` → HTTPS (Nginx)
- `3100` → Frontend (localhost only)
- `8000` → Backend (localhost only)
- Postgres, Redis, SPICE → Docker network (pas exposés)

---

## 🚨 Troubleshooting

### "API retourne 500"
**Cause:** Space-Track credentials manquants

**Fix:** Ajouter credentials (voir section ci-dessus) ou ignorer (0 satellites OK pour démo)

### "Site inaccessible"
```bash
# 1. Check containers
docker compose ps
# Tous doivent être "Up (healthy)"

# 2. Check nginx
sudo systemctl status nginx
sudo nginx -t

# 3. Check logs
docker compose logs backend | tail -50
```

### "WebSocket ne connecte pas"
```bash
# Check nginx config WebSocket
cat /etc/nginx/sites-enabled/spacex.ericcesar.com.conf | grep -A 10 "/ws"

# Should have:
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";
```

### "Frontend affiche erreurs"
```bash
# Check API depuis frontend
curl https://spacex.ericcesar.com/api/v1/satellites?limit=1

# Check browser console (F12) pour erreurs CORS
```

---

## 📦 Déploiement Complet (from scratch)

```bash
# 1. Clone repo
cd /home/clawd/prod
git clone https://github.com/e-cesar9/spacex-orbital-intelligence

# 2. Setup environnement
cd spacex-orbital-intelligence/backend
cp .env.example .env
# Editer .env avec passwords

# 3. Build et start
cd ..
docker compose up -d --build

# 4. Vérifier
./verify-prod.sh

# 5. Setup Nginx (si pas déjà fait)
sudo ln -s /etc/nginx/sites-available/spacex.ericcesar.com.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 6. Setup SSL (si pas déjà fait)
sudo certbot --nginx -d spacex.ericcesar.com
```

---

## 📝 Architecture

```
                    Internet
                       │
                       ↓
              ┌────────────────┐
              │   HTTPS (443)  │
              │   Nginx +SSL   │
              └────────┬───────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ↓              ↓              ↓
   Frontend        Backend         WebSocket
  (3100)          (8000)          (8000/ws)
     │               │                │
     │      ┌────────┴────────┐       │
     │      ↓        ↓        ↓       │
     │   Redis   Postgres  SPICE      │
     │  (6379)   (5432)   (50000)     │
     │                                │
     └────────────────────────────────┘
           Docker Network
```

---

## ✅ Checklist Production-Ready

- [x] HTTPS configuré (Let's Encrypt)
- [x] Nginx reverse proxy
- [x] Docker containers healthy
- [x] Health endpoint OK
- [x] Frontend accessible
- [x] API docs accessible
- [x] Logs structurés (JSON)
- [x] Secrets dans .env (pas hardcodés)
- [ ] Space-Track credentials (optionnel)
- [ ] Load testing (TODO)
- [ ] Monitoring Prometheus (TODO)
- [ ] Backup automatique (TODO)

---

**Date:** 2026-02-09  
**Version:** 1.0 (Production deployment)
