# Professional Monte Carlo Launch Simulator - BMAD Documentation

**Start Date:** February 10, 2026  
**Method:** BMAD (Build-Measure-Analyze-Decide) + TDD + Senior Code Standards  
**Status:** Phase 0 Starting

---

## Document Structure

```
monte-carlo-pro/
├── README.md                    ← You are here
├── 01-product-brief.md          ← Problem, users, MVP scope, metrics
├── 02-architecture.md           ← Technical decisions, system design
├── 03-epics-stories.md          ← Backlog, user stories, acceptance criteria
└── [Future: 04-sprint-log.md]  ← Daily progress tracking
```

---

## Quick Navigation

### Planning Phase (Read First)
1. **Product Brief** → Understand the problem and market
2. **Architecture** → Technical decisions and rationale
3. **Epics & Stories** → What we're building, in order

### Execution Phase (During Development)
- **PHASE-0-TRACKER.md** (in parent folder) → Detailed Week 1-2 tasks
- **OPTION-C-EXECUTION-PLAN.md** (in parent folder) → Full 6-month roadmap

---

## BMAD Method Applied

### 1. Product Brief (Build Foundation)
- **Problem:** Aerospace engineers waste 2-3 days on trade studies
- **Solution:** Fast web-based Monte Carlo simulator
- **Users:** NewSpace companies, universities
- **MVP:** 6 months, 8 phases
- **Success Metrics:** <5% validation error, 50+ users, 50%+ willing to pay

### 2. Architecture (Build Quality)
- **Decision Log:** 8 architecture decisions documented
- **Tech Stack:** Python + FastAPI + React + PostgreSQL
- **Testing:** TDD with 85%+ coverage enforced
- **Deployment:** Docker → Kubernetes (if scale needed)
- **Performance:** 100K Monte Carlo in <60s (Phase 4)

### 3. Epics & Stories (Build Clarity)
- **370 story points** across 8 phases
- **40 points/week velocity** target
- **Fibonacci estimation:** 1, 2, 3, 5, 8, 13
- **Acceptance criteria** for every story
- **Tests required** documented up-front

### 4. Sprint Execution (Build Momentum)
- **Sprint 0 (Week 1-2):** Foundation (80 points) ⚡ CRITICAL
- **Sprint 1 (Week 3-4):** Vehicle Database (21 points)
- **Sprint 2-3 (Week 5-9):** Outputs & Monte Carlo (55 points)
- [etc.]

---

## Skills Applied (Mandatory)

Every line of code follows these standards:

### From `code-quality` skill:
- ✅ **Security:** Input validation, no injection, secrets in vault
- ✅ **Robustness:** Timeouts, retries, circuit breakers
- ✅ **Performance:** No N+1, caching, profiling
- ✅ **Maintainability:** Clear names, DRY, documented

### From `tdd` skill:
- ✅ **Red-Green-Refactor:** Tests BEFORE implementation
- ✅ **Coverage:** >85% enforced by CI
- ✅ **Test Types:** Unit (60%), Integration (30%), E2E (10%)

### From `senior-code` skill:
- ✅ **Production-ready:** No "we'll fix it later"
- ✅ **Error handling:** Comprehensive, graceful degradation
- ✅ **Logging:** Structured (structlog), searchable
- ✅ **Observability:** Metrics, traces, alerts

### From `bmad-method` skill:
- ✅ **Ship fast, iterate:** MVP → validate → enhance
- ✅ **Measure everything:** Metrics before optimizing
- ✅ **Clear phases:** Decision gates at Week 2, 9, 16
- ✅ **Document as you go:** No "we'll document later"

---

## Phase Gates & Decision Points

### Gate 1: After Week 2 (Phase 0)
**Question:** Is the physics model credible?

**Metrics:**
- Validation error vs Falcon 9: ___% (target: <5%)
- Can explain ΔV budget: Yes/No
- Professional engineer review: Pass/Fail

**Decision:**
- ✅ PASS → Continue to Phase 1
- ⚠️ MARGINAL (5-10%) → Fix and revalidate
- ❌ FAIL (>10%) → Abort or hire expert

---

### Gate 2: After Week 9 (Phase 3)
**Question:** Is the core value proposition working?

**Metrics:**
- Can simulate 5+ vehicles: Yes/No
- Alpha users interested: ___/10 (target: 7+)
- Simulations run per week: ___

**Decision:**
- ✅ PASS → Continue to Phase 4
- ⚠️ MARGINAL → Pivot on features
- ❌ FAIL → Reassess market fit

---

### Gate 3: After Week 16 (Phase 6)
**Question:** Would someone pay for this?

**Metrics:**
- Beta users: ___ (target: 20+)
- Simulations per week: ___ (target: 100+)
- Willingness to pay: ___% (target: >50%)

**Decision:**
- ✅ PASS → Continue to Phase 7 or commercialize
- ⚠️ MARGINAL → Improve before launching
- ❌ FAIL → Keep free/open source, don't monetize

---

## Current Status

**Phase:** 0 (Foundation)  
**Week:** 1 of 2  
**Sprint Goal:** Validation <5% error vs Falcon 9 CRS-21  
**Current Story:** 1.1 - Refactor Vehicle Model (5 points)

**Progress:**
- [ ] Epic 1: Multi-Stage Physics (0/21 points)
- [ ] Epic 2: Improved Physics (0/21 points)
- [ ] Epic 3: Falcon 9 Validation (0/38 points)

**Blockers:** None yet

**Next Actions:**
1. Start Story 1.1 (Refactor Vehicle Model)
2. Write tests for Stage and Vehicle classes
3. Implement staging support
4. Move to Story 1.2 (Staging Logic)

---

## How to Use These Docs

### For Rico (Developer):
1. **Starting a new sprint:** Read sprint goal in 03-epics-stories.md
2. **Starting a story:** Read acceptance criteria, write tests first (TDD)
3. **During development:** Follow code-quality, senior-code standards
4. **Completing a story:** All tests pass, criteria met, code reviewed
5. **Weekly:** Update sprint log, review metrics

### For James (PM/Validation):
1. **Weekly check-in:** Review progress vs sprint goal
2. **Phase gates:** Evaluate metrics, make go/no-go decision
3. **User research:** Interview 5-10 users per phase
4. **Validation:** Review physics accuracy, document results
5. **Documentation:** Keep README.md, architecture, stories updated

### For Future Contributors:
1. Read **Product Brief** first (understand the why)
2. Read **Architecture** (understand the how)
3. Pick a story from **Epics & Stories** (P0 first!)
4. Follow **Testing Standards** (TDD, 85% coverage)
5. Submit PR with tests and documentation

---

## Documentation Philosophy

**From BMAD Method:**
> "Document as you build, not after."

**Every document is:**
- **Living:** Updated as decisions change
- **Actionable:** Clear next steps
- **Measurable:** Concrete metrics
- **Decidable:** Go/no-go criteria

**Not this:**
- ❌ "We'll document it later" (no, now)
- ❌ "It's obvious from the code" (no, write it down)
- ❌ "This is just for me" (no, for future you and others)

---

## Success Metrics Dashboard

**Technical:**
- Validation accuracy: ___ % (target: <5%)
- Test coverage: ___ % (target: >85%)
- Performance (100K runs): ___ s (target: <60s)

**Product:**
- Alpha users: ___ (target: 5-10 by Week 9)
- Beta users: ___ (target: 20+ by Week 16)
- Simulations/week: ___ (target: 100+ by Week 16)

**Business:**
- Willing to pay: ___ % (target: >50% by Week 16)
- Paying customers: ___ (target: 10+ by Week 24)
- MRR: $___ (target: $1k-10k by Week 24)

---

## Links & Resources

**Internal:**
- [Parent BMAD folder](../README.md) - All BMAD planning docs
- [Phase 0 Tracker](../PHASE-0-TRACKER.md) - Detailed Week 1-2 plan
- [Option C Execution Plan](../OPTION-C-EXECUTION-PLAN.md) - Full 6-month roadmap
- [Enterprise Evaluation](../../MONTE-CARLO-ENTERPRISE-EVALUATION.md) - Why we're doing this

**External:**
- BMAD Method: https://github.com/bmad-code-org/BMAD-METHOD
- SpaceX User Guide: https://www.spacex.com/media/falcon-users-guide.pdf
- US Standard Atmosphere: https://ntrs.nasa.gov/citations/19770009539
- Vallado Textbook: "Fundamentals of Astrodynamics and Applications"

**Community:**
- r/aerospace - User research
- r/spacex - Technical discussions
- Discord (future) - Community support

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-09 | Initial BMAD structure created | James |
| 2026-02-10 | Phase 0 started | Rico |
| [Future] | ... | ... |

---

**Status:** ✅ Planning Complete, Execution Starting  
**Owner:** Rico (dev) + James (PM/validation)  
**Review Cadence:** Weekly (Sundays)  
**Next Review:** February 16, 2026 (end of Week 1)

🚀 **Let's build something that matters.**
