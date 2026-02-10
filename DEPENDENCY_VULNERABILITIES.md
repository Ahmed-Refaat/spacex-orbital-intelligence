# Dependency Vulnerability Scan Report

**Date:** February 10, 2026  
**Tool:** pip-audit 2.10.0  
**Status:** 🟠 6 known vulnerabilities found in 4 packages

---

## 📊 Summary

| Package | Current | Fixed | Severity | CVEs |
|---------|---------|-------|----------|------|
| pip | 24.0 | 26.0+ | HIGH | 2 |
| python-multipart | 0.0.18 | 0.0.22 | MEDIUM | 1 |
| starlette | 0.41.3 | 0.49.1 | HIGH | 2 |
| wheel | 0.45.1 | 0.46.2 | HIGH | 1 |

---

## 🔴 Critical Vulnerabilities

### 1. **pip** (2 CVEs)

**Current:** 24.0  
**Fixed:** 26.0+

#### CVE-2025-8869
- **Severity:** HIGH
- **Issue:** Tar archive extraction may not check symbolic links
- **Impact:** Path traversal when extracting sdists
- **Mitigation:** Upgrade pip to 25.3+ or use Python >=3.12

#### CVE-2026-1703
- **Severity:** HIGH
- **Issue:** Path traversal in wheel extraction
- **Impact:** Files extracted outside installation directory
- **Mitigation:** Upgrade pip to 26.0+

---

### 2. **starlette** (2 CVEs)

**Current:** 0.41.3  
**Fixed:** 0.49.1

#### CVE-2025-54121
- **Severity:** MEDIUM
- **Issue:** File upload blocks event loop during rollover
- **Impact:** DoS via large file uploads
- **Affected:** FileResponse with files > default spool size
- **Mitigation:** Upgrade to starlette 0.47.2+

#### CVE-2025-62727
- **Severity:** HIGH
- **Issue:** Quadratic-time Range header parsing
- **Impact:** CPU exhaustion DoS
- **Affected:** FileResponse, StaticFiles
- **Mitigation:** Upgrade to starlette 0.49.1+

---

### 3. **python-multipart** (1 CVE)

**Current:** 0.0.18  
**Fixed:** 0.0.22

#### CVE-2026-24486
- **Severity:** MEDIUM
- **Issue:** Path traversal with UPLOAD_KEEP_FILENAME=True
- **Impact:** Arbitrary file write to attacker-controlled paths
- **Affected:** Only when UPLOAD_DIR + UPLOAD_KEEP_FILENAME=True
- **Mitigation:** Upgrade to 0.0.22 or avoid UPLOAD_KEEP_FILENAME

---

### 4. **wheel** (1 CVE)

**Current:** 0.45.1  
**Fixed:** 0.46.2

#### CVE-2026-24049
- **Severity:** HIGH
- **Issue:** Path traversal in wheel unpack
- **Impact:** Arbitrary file permission modification
- **Affected:** wheel.cli.unpack function
- **Mitigation:** Upgrade to wheel 0.46.2+

---

## ✅ Recommended Fixes

### Update requirements.txt

```txt
# Security updates
pip>=26.0
wheel>=0.46.2
python-multipart>=0.0.22
starlette>=0.49.1
fastapi>=0.116.0  # Depends on starlette 0.49.1+
```

### Upgrade Commands

```bash
# Inside Docker container or venv
pip install --upgrade pip>=26.0
pip install --upgrade wheel>=0.46.2
pip install --upgrade python-multipart>=0.0.22
pip install --upgrade starlette>=0.49.1
pip install --upgrade fastapi>=0.116.0
```

---

## 🛡️ Risk Assessment

### Current Risk Level: 🟠 MEDIUM-HIGH

**Exploitable in this application:**

1. **starlette CVE-2025-62727** (Range DoS) - ✅ **YES**
   - We use StaticFiles and FileResponse
   - Unauthenticated remote DoS possible
   - **Priority:** P0 (Fix immediately)

2. **python-multipart CVE-2026-24486** - ❌ **NO**
   - We don't use UPLOAD_KEEP_FILENAME=True
   - Default config is safe

3. **pip/wheel CVEs** - 🟡 **LOW**
   - Only exploitable during package installation
   - Not runtime vulnerabilities
   - **Priority:** P1 (Fix during next maintenance)

### Impact if Not Fixed

- **starlette Range DoS:** Site unavailable via crafted Range headers
- **Other CVEs:** Low impact in our current configuration

---

## 📋 Action Plan

### Immediate (Today)
- [x] Run vulnerability scan
- [x] Document findings
- [ ] Upgrade starlette to 0.49.1+ (P0)
- [ ] Upgrade python-multipart to 0.0.22 (P1)
- [ ] Test application after upgrades
- [ ] Rebuild Docker image
- [ ] Deploy

### This Week
- [ ] Upgrade pip to 26.0+
- [ ] Upgrade wheel to 0.46.2+
- [ ] Add pip-audit to CI/CD pipeline
- [ ] Schedule monthly dependency scans

---

## 🔄 Monitoring

### Automated Scanning

Add to CI/CD:
```yaml
# .github/workflows/security.yml
- name: Dependency Vulnerability Scan
  run: |
    pip install pip-audit
    pip-audit --format json > audit-report.json
    pip-audit --format markdown >> $GITHUB_STEP_SUMMARY
```

### Monthly Review

- Run `pip-audit` first Monday of each month
- Review and upgrade vulnerable dependencies
- Document exceptions if upgrade blocked

---

**Last Scanned:** February 10, 2026  
**Next Scan Due:** March 3, 2026
