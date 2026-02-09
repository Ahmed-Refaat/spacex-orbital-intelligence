# Epics & Stories - Quality Improvements Sprint

**Sprint Goal:** Fix all P0 + P1 issues (10 total)  
**Timeline:** 6 days  
**Story Points Total:** 34 points

---

## Epic 1: Backend Security & Robustness (16 points)

### Story 1.1: Fix Exception Handling (P0-3) - 3 points
**As a** developer  
**I want** specific exception handlers  
**So that** errors are properly categorized and logged

**Acceptance Criteria:**
- [ ] ValidationError handler returns 422 with error details
- [ ] HTTPException handler logs and re-raises
- [ ] Generic Exception handler only catches truly unhandled
- [ ] All handlers log with structlog
- [ ] Test: Trigger validation error → 422 response
- [ ] Test: Trigger HTTPException → correct status code

**Files:**
- `backend/app/main.py`
- `backend/tests/test_exception_handlers.py` (NEW)

---

### Story 1.2: Mandatory API Key in Production (P0-4) - 2 points
**As a** ops engineer  
**I want** API key to be mandatory in production  
**So that** there's no silent security degradation

**Acceptance Criteria:**
- [ ] `get_api_key()` raises RuntimeError if `ENV=production` and no key
- [ ] Dev mode still generates temporary key with warning
- [ ] Error message includes instructions to generate key
- [ ] Update SECURITY.md with deployment checklist
- [ ] Test: Production mode without key → RuntimeError
- [ ] Test: Dev mode without key → temporary key + warning

**Files:**
- `backend/app/core/security.py`
- `backend/tests/test_security.py`
- `SECURITY.md`

---

### Story 1.3: Form Input Validation (P1-7) - 3 points
**As a** backend developer  
**I want** OMM upload form validated with Pydantic  
**So that** malicious input is rejected early

**Acceptance Criteria:**
- [ ] Create `OMMUploadForm` model with constraints
- [ ] `source` field: max_length=100, pattern `^[a-zA-Z0-9_-]+$`
- [ ] Sanitizer strips/lowercases source
- [ ] Update endpoint to use `Depends(OMMUploadForm)`
- [ ] Test: Valid source → accepted
- [ ] Test: SQL injection attempt → 422 error
- [ ] Test: XSS attempt → 422 error

**Files:**
- `backend/app/models/omm.py` (NEW)
- `backend/app/api/satellites.py`
- `backend/tests/test_omm_validation.py` (NEW)

---

### Story 1.4: Prefixed Cache Keys (P1-9) - 2 points
**As a** backend developer  
**I want** all cache keys prefixed with namespace  
**So that** there's no collision with other services

**Acceptance Criteria:**
- [ ] Add `cache_prefix` to Settings
- [ ] CacheService._make_key() adds prefix
- [ ] Update all cache calls to use prefixed keys
- [ ] Test: Cache set/get with prefix
- [ ] Test: Verify keys in Redis have prefix

**Files:**
- `backend/app/core/config.py`
- `backend/app/services/cache.py`
- `backend/tests/test_cache_prefix.py` (NEW)

---

### Story 1.5: Circuit Breaker on External Calls (P1-10) - 6 points
**As a** backend developer  
**I want** circuit breaker on external API calls  
**So that** failures don't cascade

**Acceptance Criteria:**
- [ ] Wrap `SpaceXClient.get_starlink_satellites()` with @circuit
- [ ] Wrap `TLEService.fetch_celestrak()` with @circuit
- [ ] Wrap `SpiceClient` calls with @circuit
- [ ] Configure: failure_threshold=5, recovery_timeout=60s
- [ ] Test: Simulate 5 failures → circuit opens
- [ ] Test: Circuit open → immediate failure
- [ ] Test: After timeout → half-open → retry

**Files:**
- `backend/app/services/spacex_api.py`
- `backend/app/services/tle_service.py`
- `backend/app/services/spice_client.py`
- `backend/tests/test_circuit_breaker.py` (NEW)

---

## Epic 2: Frontend Performance & UX (12 points)

### Story 2.1: Batch API Calls (P0-1) - 3 points
**As a** user  
**I want** initial page load to be fast  
**So that** I see satellites quickly

**Acceptance Criteria:**
- [ ] Create `getInitialData()` batch function
- [ ] Use `Promise.all()` for parallel fetch
- [ ] Update App.tsx to use React Query with batch
- [ ] Remove sequential API calls
- [ ] Test: Measure load time (target <500ms)
- [ ] Lighthouse performance score >85

**Files:**
- `frontend/src/services/api.ts`
- `frontend/src/App.tsx`
- `frontend/tests/api.test.ts` (NEW)

---

### Story 2.2: Replace Global Mutation with useRef (P0-2) - 2 points
**As a** developer  
**I want** orbit controls managed via React ref  
**So that** code is type-safe and testable

**Acceptance Criteria:**
- [ ] Create `useOrbitControls()` hook
- [ ] Replace `window.__orbitControls` with `controlsRef`
- [ ] Update zoom handlers to use ref
- [ ] Remove global type declaration
- [ ] Test: Zoom in/out works
- [ ] Test: No window mutation

**Files:**
- `frontend/src/hooks/useOrbitControls.ts` (NEW)
- `frontend/src/components/Globe/Globe.tsx`

---

### Story 2.3: Add Error Boundary (P0-5) - 2 points
**As a** user  
**I want** app to show error message instead of crashing  
**So that** I can recover from errors

**Acceptance Criteria:**
- [ ] Create ErrorBoundary component
- [ ] Wrap <Globe /> in ErrorBoundary
- [ ] Show fallback UI with reload button
- [ ] Log errors to console (future: send to monitoring)
- [ ] Test: Simulate Three.js crash → fallback shown
- [ ] Test: Reload button works

**Files:**
- `frontend/src/components/ErrorBoundary.tsx` (NEW)
- `frontend/src/App.tsx`
- `frontend/tests/ErrorBoundary.test.tsx` (NEW)

---

### Story 2.4: Runtime Validation with Zod (P1-6) - 3 points
**As a** developer  
**I want** API responses validated at runtime  
**So that** bad data doesn't cause crashes

**Acceptance Criteria:**
- [ ] Install `zod` dependency
- [ ] Create Zod schemas for key types
- [ ] Wrap API calls with schema validation
- [ ] Handle validation errors gracefully
- [ ] Test: Valid response → parsed correctly
- [ ] Test: Invalid response → error thrown

**Files:**
- `frontend/package.json`
- `frontend/src/types/schemas.ts` (NEW)
- `frontend/src/services/api.ts`
- `frontend/tests/validation.test.ts` (NEW)

---

### Story 2.5: Code Splitting & Lazy Loading (P1-8) - 2 points
**As a** user  
**I want** fast initial page load  
**So that** I see content immediately

**Acceptance Criteria:**
- [ ] Lazy load Sidebar tabs (except Satellites)
- [ ] Add Suspense with skeleton fallback
- [ ] Configure Vite manual chunks
- [ ] Test: Initial bundle <200KB
- [ ] Test: Tabs load on demand
- [ ] Lighthouse performance >85

**Files:**
- `frontend/src/components/Sidebar/Sidebar.tsx`
- `frontend/vite.config.ts`
- `frontend/tests/bundle-size.test.ts` (NEW)

---

## Epic 3: Testing & Documentation (6 points)

### Story 3.1: Add Backend Tests - 3 points
**As a** developer  
**I want** comprehensive test coverage  
**So that** regressions are caught early

**Acceptance Criteria:**
- [ ] Test exception handlers (3 scenarios)
- [ ] Test API key enforcement (prod/dev)
- [ ] Test form validation (valid/invalid)
- [ ] Test cache prefix
- [ ] Test circuit breaker (open/close/half-open)
- [ ] Coverage >80%

**Files:**
- `backend/tests/test_exception_handlers.py`
- `backend/tests/test_security.py`
- `backend/tests/test_omm_validation.py`
- `backend/tests/test_cache_prefix.py`
- `backend/tests/test_circuit_breaker.py`

---

### Story 3.2: Add Frontend Tests - 2 points
**As a** developer  
**I want** frontend tests for critical paths  
**So that** UI doesn't break

**Acceptance Criteria:**
- [ ] Test ErrorBoundary component
- [ ] Test API batching
- [ ] Test Zod validation
- [ ] Test lazy loading
- [ ] Test useOrbitControls hook

**Files:**
- `frontend/tests/ErrorBoundary.test.tsx`
- `frontend/tests/api.test.ts`
- `frontend/tests/validation.test.ts`

---

### Story 3.3: Update Documentation - 1 point
**As a** ops engineer  
**I want** updated deployment docs  
**So that** I know how to deploy safely

**Acceptance Criteria:**
- [ ] Update SECURITY.md with ENV=production requirement
- [ ] Update README with new dependencies (zod)
- [ ] Add deployment checklist
- [ ] Document circuit breaker configuration

**Files:**
- `SECURITY.md`
- `README.md`
- `DEPLOYMENT.md`

---

## Sprint Backlog Summary

| Epic | Stories | Points | Priority |
|------|---------|--------|----------|
| Backend Security | 5 | 16 | P0+P1 |
| Frontend Performance | 5 | 12 | P0+P1 |
| Testing & Docs | 3 | 6 | P1 |
| **Total** | **13** | **34** | |

---

## Sprint Schedule

### Day 1-2: Backend (16 points)
- Story 1.1: Exception handling ✅
- Story 1.2: API key mandatory ✅
- Story 1.3: Form validation ✅
- Story 1.4: Cache prefix ✅
- Story 1.5: Circuit breaker ✅

### Day 3-4: Frontend (12 points)
- Story 2.1: Batch API calls ✅
- Story 2.2: useRef pattern ✅
- Story 2.3: Error Boundary ✅
- Story 2.4: Zod validation ✅
- Story 2.5: Code splitting ✅

### Day 5: Testing (6 points)
- Story 3.1: Backend tests ✅
- Story 3.2: Frontend tests ✅
- Story 3.3: Documentation ✅

### Day 6: Deploy + Monitor
- Deploy backend (production)
- Deploy frontend (build + Nginx)
- Monitor errors/performance
- Lighthouse audit

### Day 7: Buffer
- Handle any issues
- Final validation

---

## Definition of Done

**Story level:**
- [ ] Code implemented
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Documentation updated

**Sprint level:**
- [ ] All P0+P1 stories complete
- [ ] Test coverage >80%
- [ ] Lighthouse score >85
- [ ] Bundle size <300KB
- [ ] Deployed to production
- [ ] No critical bugs

---

## Next: Implementation

Execute stories in order. Each story = separate commit for easy rollback.

Start with Story 1.1 (Exception Handling).
