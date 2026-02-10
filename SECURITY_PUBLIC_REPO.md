# 🔒 SÉCURITÉ POUR UN REPO PUBLIC

Ce repository est **PUBLIC** sur GitHub. Voici comment maintenir la sécurité.

---

## ✅ CE QUI EST PUBLIC (OK)

- ✅ Code source (backend, frontend)
- ✅ Architecture et documentation
- ✅ Dockerfile et docker-compose.yml (structure)
- ✅ Tests et CI/CD configuration
- ✅ Rapports d'audit (avec secrets redactés)

---

## ❌ CE QUI NE DOIT JAMAIS ÊTRE PUBLIC

### 1. Credentials & Secrets

**❌ JAMAIS committer:**
```
.env
*.env
*.pem
*.key
id_rsa*
*.p12
*.jks
credentials.json
secrets.yaml
```

**✅ À la place:**
```
.env.example          # Template sans valeurs réelles
backend/.env.example  # Template avec explications
```

### 2. Données Sensibles

**❌ JAMAIS committer:**
```
TLE data (si propriétaire)
Telemetry logs
Customer data
Production configs
Database dumps
```

### 3. Infrastructure Details

**❌ JAMAIS committer:**
```
Production IPs
SSH keys
API tokens
Database passwords
Internal URLs
```

---

## 🛡️ PROTECTIONS EN PLACE

### 1. `.gitignore` Strict

```gitignore
# Environment files
.env
.env.*
!.env.example

# Credentials
*.pem
*.key
credentials/
secrets/

# Sensitive data
*.db
*.sqlite
data/production/
```

### 2. GitHub Actions - Secret Scanning

Fichier: `.github/workflows/security-scan.yml`

**Détecte automatiquement:**
- Secrets dans les commits
- Vulnérabilités dans les dépendances
- Problèmes dans les Dockerfiles

**Bloque le merge** si secrets détectés.

### 3. Pre-commit Hooks (optionnel)

Installation:
```bash
pip install pre-commit
pre-commit install
```

Configuration `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

---

## 🔄 WORKFLOW DE DÉVELOPPEMENT SÉCURISÉ

### 1. Avant de Committer

```bash
# Vérifier qu'aucun secret n'est staged
git diff --cached | grep -i "password\|secret\|key\|token"

# Si quelque chose apparaît → NE PAS COMMITTER
# Retirer le fichier:
git reset HEAD path/to/file

# L'ajouter au .gitignore
echo "path/to/file" >> .gitignore
```

### 2. Configuration Locale

**Stockage sécurisé des secrets:**
```bash
# Option 1: Fichier .env local (gitignored)
cp backend/.env.example backend/.env
# Éditer backend/.env avec les vraies valeurs

# Option 2: Variables d'environnement système
export REDIS_PASSWORD="your_password_here"
export POSTGRES_PASSWORD="your_password_here"

# Option 3: Secret manager (production)
# AWS Secrets Manager, HashiCorp Vault, etc.
```

### 3. Partage de Secrets (équipe)

**❌ JAMAIS par:**
- Email
- Slack/Teams
- Git
- GitHub Issues
- Discord

**✅ Utiliser:**
- 1Password / Bitwarden (vault partagé)
- AWS Secrets Manager
- HashiCorp Vault
- Encrypted file avec GPG

---

## 🚨 SI UN SECRET EST EXPOSÉ

### Action Immédiate (dans l'heure)

1. **Invalider le secret**
   ```bash
   # Changer immédiatement:
   - Database passwords
   - API keys
   - SSH keys
   - Tokens
   ```

2. **Notifier l'équipe**
   ```
   Slack: @here SECRET LEAKED in commit abc123
   Action: Rotating credentials NOW
   ETA: 30 minutes
   ```

3. **Vérifier les logs d'accès**
   ```bash
   # Vérifier si le secret a été utilisé
   - Database access logs
   - API usage logs
   - SSH login attempts
   ```

### Nettoyage de l'Historique Git

**⚠️ ATTENTION:** Réécrire l'historique est dangereux.

**Option 1: BFG Repo Cleaner (recommandé)**
```bash
# Download BFG
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# Backup
git clone --mirror git@github.com:user/repo.git repo-backup

# Clean
java -jar bfg-1.14.0.jar --replace-text passwords.txt repo.git
cd repo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (⚠️ casse l'historique pour tout le monde)
git push --force
```

**Option 2: git-filter-repo**
```bash
pip install git-filter-repo

# Remove file from all history
git filter-repo --path backend/.env --invert-paths

# Force push
git push --force --all
```

**⚠️ Après force push:**
- Tous les collaborateurs doivent re-clone
- Les PR ouverts sont cassés
- Les forks gardent l'ancien historique

**Alternative:** Faire un nouveau repo clean si faisable.

---

## 📋 CHECKLIST AVANT CHAQUE COMMIT

```bash
# 1. Vérifier les fichiers stagés
git status

# 2. Vérifier le contenu
git diff --cached

# 3. Chercher des patterns suspects
git diff --cached | grep -iE "password|secret|key|token|api_key|private"

# 4. Si doute, annuler
git reset HEAD <file>

# 5. Ajouter au .gitignore si nécessaire
echo "<file>" >> .gitignore
git add .gitignore
```

---

## 🔐 BONNES PRATIQUES

### 1. Utiliser des Templates

**backend/.env.example:**
```bash
# Database Credentials (CHANGE IN PRODUCTION)
REDIS_PASSWORD=generate_with_openssl_rand
POSTGRES_PASSWORD=generate_with_openssl_rand

# API Keys (GET FROM PROVIDER)
SPACETRACK_USERNAME=your_email@example.com
SPACETRACK_PASSWORD=your_password

# Security
SPACEX_API_KEY=generate_with_secrets_token_urlsafe_32

# Génération de secrets sécurisés:
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Rotation Régulière

**Calendrier:**
- Database passwords: 90 jours
- API keys: 180 jours
- SSH keys: 365 jours
- Tokens: 30 jours

### 3. Principe du Moindre Privilège

```bash
# Permissions fichiers
chmod 600 backend/.env        # Owner read/write only
chmod 700 backend/            # Owner access only

# Permissions Docker
docker-compose.yml:
  secrets:
    redis_password:
      file: ./secrets/redis_password.txt
    postgres_password:
      file: ./secrets/postgres_password.txt
```

### 4. Audit Trail

**Qui a accès aux secrets?**
```bash
# Créer un fichier d'audit (gitignored)
echo "# Secret Access Log" > secrets/ACCESS_LOG.md
echo "- 2026-02-10: Rico - Initial setup" >> secrets/ACCESS_LOG.md
echo "- 2026-02-10: James - Rotation after exposure" >> secrets/ACCESS_LOG.md
```

---

## 🎓 FORMATION ÉQUIPE

### Onboarding Nouveau Dev

**Checklist:**
- [ ] Lire ce document
- [ ] Installer pre-commit hooks
- [ ] Configurer .env local
- [ ] Tester le workflow (commit test)
- [ ] Accès au vault de secrets (1Password)

### Quiz Sécurité

**Q1:** Je veux partager un password avec un collègue. Quel moyen?
- ❌ Slack
- ❌ Email
- ✅ 1Password shared vault

**Q2:** J'ai committé un secret par erreur. Il n'est pas encore pushé. Que faire?
- ❌ Pusher quand même
- ❌ Ajouter un commit "remove secret"
- ✅ `git reset HEAD~1` et recommencer

**Q3:** Le CI/CD a détecté un secret. Que faire?
- ❌ Ignorer l'alerte
- ❌ Bypasser le check
- ✅ Retirer le secret, invalider credentials, recommencer

---

## 📞 CONTACTS

**Security Officer:** [À désigner]  
**Incident Response:** [À définir]  
**Secret Rotation SOP:** [Document séparé]

---

## 📚 RESSOURCES

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12-Factor App: Config](https://12factor.net/config)
- [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

---

**Dernière mise à jour:** 2026-02-10  
**Version:** 1.0  
**Status:** ✅ ACTIF
