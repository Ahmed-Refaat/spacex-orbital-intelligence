# Product Brief - Professional Monte Carlo Launch Simulator

**Date:** 2026-02-09  
**Owner:** Rico  
**Status:** Planning → Build  
**Method:** BMAD + TDD + Senior Code Standards

---

## Problem Statement

Aerospace engineering teams waste **2-3 days** on preliminary mission design tasks that should take **30 minutes**. Existing tools are either:
- **Too expensive:** STK costs $50k-200k/year per seat
- **Too slow:** GMAT/STK Monte Carlo runs take hours/days
- **Too old:** Desktop apps from 2005, no collaboration
- **Too complex:** Steep learning curve, overkill for early-phase design

**Result:** Small aerospace companies (NewSpace startups, university labs) either:
1. Waste engineering time on manual Excel + MATLAB studies
2. Pay for STK licenses they can't afford
3. Make design decisions without proper uncertainty quantification

---

## Target Users

### Primary: NewSpace Engineering Teams
- **Who:** Systems engineers, mission analysts, propulsion engineers
- **Companies:** Rocket Lab, Relativity Space, Firefly, Astra, university CubeSat programs
- **Size:** 5-50 person engineering teams
- **Budget:** <$100k/year for tools (can't afford STK)
- **Pain:** Need fast trade studies for preliminary design reviews

**User Persona: Sarah, Systems Engineer at NewSpace Startup**
- Age: 28-35, aerospace engineering background
- Uses: MATLAB, Python, Excel, Git
- Frustration: "I spend 3 days setting up STK models for a 30-minute design review"
- Needs: "Just tell me if we can launch 15,000 kg to LEO with 95% confidence"

### Secondary: Educators & Hobbyists
- **Who:** Aerospace professors, students, KSP players, science communicators
- **Pain:** Teach orbital mechanics without expensive software
- **Needs:** Realistic simulation tool, free or cheap, web-based

---

## Core Value Proposition

**"Preliminary mission design in minutes, not days"**

**Before (without tool):**
- Trade study: 2-3 days (STK setup + runs + Excel analysis)
- Monte Carlo: Impossible or manual Python scripts
- Collaboration: Email Excel files back and forth

**After (with tool):**
- Trade study: 30 minutes (select vehicle + mission + compare)
- Monte Carlo: Built-in (10,000 runs in <1 minute)
- Collaboration: Share URL, real-time results

**Key Differentiators:**
1. **Speed:** 100x faster Monte Carlo than STK (GPU acceleration)
2. **Accessibility:** Web-based, zero installation, works on any device
3. **Cost:** Free tier or $99/month vs $50k+/year
4. **Modern UX:** Consumer-grade interface, not enterprise desktop app from 2005
5. **Open Core:** Physics engine open source = trust + community

---

## MVP Scope (6 Months)

### P0 - Must Have (Phase 0-3, Weeks 1-9)

**Core Simulation:**
- [x] Multi-stage vehicle support (2+ stages)
- [x] Physics: Gravity variation, US Std Atmosphere, RK4 integration
- [ ] 5+ real vehicles (Falcon 9, Ariane 6-2/6-4, Atlas V, Long March)
- [ ] 3+ mission types (LEO, GTO, Sun-sync)
- [ ] Validated <5% error vs real flights (Falcon 9, etc.)

**Outputs:**
- [ ] ΔV budget breakdown (gravity, drag, steering losses)
- [ ] Trajectory plots (altitude, velocity, downrange, Q, g-load)
- [ ] Orbital elements (apogee, perigee, inclination, etc.)
- [ ] CSV export (full trajectory data)

**Monte Carlo:**
- [ ] Realistic parameter distributions (manufacturing, environment, operations)
- [ ] Parameter correlations (thrust ↔ Isp, etc.)
- [ ] Confidence intervals (50%, 95%, 99%)
- [ ] Sensitivity analysis (tornado diagram)

### P1 - Should Have (Phase 4-6, Weeks 10-16)

**Performance:**
- [ ] GPU acceleration (100K runs in <1 min)
- [ ] 10-100x speedup vs current implementation

**UX:**
- [ ] Redesigned frontend (task-oriented navigation)
- [ ] Batch processing (compare 10+ configs)
- [ ] Simulation library (save/load/search)
- [ ] Shareable URLs

**Trust:**
- [ ] Validation dashboard (show results publicly)
- [ ] Complete documentation (physics, validation, API)
- [ ] User guide with examples

### P2 - Nice to Have (Phase 7-8, Weeks 17-24)

**Advanced:**
- [ ] Optimization engine (auto-find best pitch program)
- [ ] 3D visualization (trajectory in space)
- [ ] Integration APIs (REST, Python client)
- [ ] Production deployment (Kubernetes, auth, monitoring)

**Out of Scope (v1.0):**
- Detailed mission planning (use STK/GMAT for that)
- Spacecraft subsystems (power, thermal, comms)
- Ground operations (launch procedures, tracking)
- Real-time flight simulation (we do preliminary design only)

---

## Success Metrics

### Technical Metrics
- **Validation accuracy:** <5% error vs real flights (blocker if >10%)
- **Performance:** 100K Monte Carlo runs in <60s
- **Availability:** 99.9% uptime in production
- **Test coverage:** >85% (enforced by CI)

### Product Metrics
- **Week 2 (Phase 0):** Validation passing
- **Week 9 (Phase 3):** 5+ alpha users actively using
- **Week 16 (Phase 6):** 20+ beta users, 100+ simulations/week
- **Week 24 (Phase 8):** 50+ active users, 1000+ simulations/month

### Business Metrics (if monetizing)
- **Week 16:** 50%+ users willing to pay
- **Week 24:** 10+ paying customers OR 100+ free users
- **Month 12:** $50k-500k ARR (500-5000 pro users at $99/month)

### Qualitative Metrics
- User testimonial: "This saved me 2 days on my last design review"
- External validation: Aerospace professor review or conference paper
- GitHub stars: 500+ (if open source)
- Press mention: TechCrunch, Ars Technica, or r/space front page

---

## Constraints

### Technical
- **Physics accuracy:** Non-negotiable, must validate <5%
- **Performance:** Must be fast enough for interactive use (<5s feedback)
- **Platform:** Web-based (React frontend, Python backend)
- **Open core:** Simulation engine must be open source for trust

### Time
- **Phase 0 (Foundation):** 2 weeks MAXIMUM (kill switch if validation fails)
- **Phase 1-3 (MVP):** 9 weeks total
- **Phase 4-6 (Professional):** 16 weeks total
- **Phase 7-8 (Advanced):** 24 weeks total
- **Total:** 6 months to production-ready

### Budget
- **Development:** $0-10k (infrastructure, validation review, contractors)
- **Operations:** $100-500/month (cloud hosting scales with usage)
- **Total first year:** $5-15k

### Resources
- **Core dev:** Rico (fullstack) + James (strategy, doc, validation)
- **Optional:** Aerospace engineer for validation review ($2-5k one-time)
- **Users:** Need 50+ user interviews across 6 months

---

## Timeline

```
Phase 0 (Weeks 1-2):   Foundation ⚡ CRITICAL
  ├─ Multi-stage support
  ├─ Physics improvements
  ├─ Falcon 9 configuration
  └─ Validation <5% error ← GATE 1

Phase 1-3 (Weeks 3-9): Core MVP
  ├─ Vehicle database (5+ vehicles)
  ├─ Actionable outputs (ΔV, plots, exports)
  └─ Monte Carlo professional ← GATE 2

Phase 4-6 (Weeks 10-16): Professional
  ├─ Performance (GPU acceleration)
  ├─ UX overhaul
  └─ Validation & trust ← GATE 3

Phase 7-8 (Weeks 17-24): Advanced (optional)
  ├─ Optimization, 3D viz, APIs
  └─ Production hardening
```

**Phase Gates:**
- **Gate 1 (Week 2):** Validation passes? → Continue / Fix / Abort
- **Gate 2 (Week 9):** Users interested? → Continue / Pivot
- **Gate 3 (Week 16):** Willing to pay? → Commercialize / Open source / Consulting

---

## Risks & Mitigation

### High Risk: Validation Fails (>10% error)
**Impact:** BLOCKER - Tool is not credible  
**Mitigation:** Start with well-documented reference (Falcon 9), validate early  
**Contingency:** Hire aerospace PhD for physics review ($2-5k)

### High Risk: No Market Interest
**Impact:** CRITICAL - Wasted 6 months  
**Mitigation:** Talk to 50+ users across development, validate demand weekly  
**Contingency:** Pivot to education market or shut down

### Medium Risk: Performance Not Fast Enough
**Impact:** MAJOR - Tool too slow for interactive use  
**Mitigation:** Profile early, optimize in Phase 4, GPU acceleration  
**Contingency:** Cloud GPU for heavy Monte Carlo, reduce default sample size

### Medium Risk: Burn Out
**Impact:** MAJOR - Project abandoned  
**Mitigation:** Sustainable pace (25h/week not 80h), phases allow recovery  
**Contingency:** Extend timeline or find co-founder

### Low Risk: Can't Compete with STK
**Impact:** MINOR - Different market segments  
**Mitigation:** Don't try to replace STK, focus on preliminary design niche  
**Contingency:** Position as complement, not replacement

---

## Go/No-Go Criteria

### After Phase 0 (Week 2):
**GO if:** ✅ Validation <5%, physics credible, motivated  
**NO-GO if:** ❌ Validation >10%, physics fundamentally wrong, lost motivation

### After Phase 3 (Week 9):
**GO if:** ✅ 5+ alpha users, positive feedback, clear path forward  
**NO-GO if:** ❌ <3 users, "nice but won't use it", no market

### After Phase 6 (Week 16):
**GO if:** ✅ 20+ beta users, 50%+ willing to pay, validations passing  
**NO-GO if:** ❌ <10 users, <30% willing to pay, validation issues

---

## Dependencies

**External:**
- Vehicle parameters (public sources: SpaceX website, Wikipedia, user guides)
- Flight data for validation (webcast telemetry, NASA reports)
- US Standard Atmosphere 1976 (NASA publication, free)
- Beta users (need to recruit 5-10 in first month)

**Internal:**
- Current codebase (spacex-orbital-intelligence, already deployed)
- Existing infrastructure (Docker, Nginx, Redis, PostgreSQL)
- Skills available: bmad-method, code-quality, tdd, senior-code

**Nice to Have:**
- Academic validation (professor review or conference paper)
- Press coverage (TechCrunch, Ars Technica)
- Community support (aerospace subreddit, Discord)

---

## Skills Applied (Non-Negotiable)

Every phase follows these standards:

**From code-quality skill:**
- ✅ Security first (input validation, no injection, secrets in vault)
- ✅ Robustness (timeouts, retries, circuit breakers, graceful degradation)
- ✅ Performance (no N+1, pagination, caching, profiling)
- ✅ Maintainability (clear names, small functions, DRY, documented)

**From tdd skill:**
- ✅ Red-Green-Refactor cycle for all new code
- ✅ Tests written BEFORE implementation
- ✅ >85% coverage enforced by CI
- ✅ Validation tests are integration tests (not just unit)

**From senior-code skill:**
- ✅ Production-ready from day 1 (no "we'll fix it later")
- ✅ Error handling comprehensive
- ✅ Logging structured (structlog)
- ✅ Observability built-in (metrics, traces)

**From bmad-method skill:**
- ✅ Ship fast, iterate (MVP → validate → enhance)
- ✅ Measure everything (metrics before optimizing)
- ✅ Clear phases with decision gates
- ✅ Documentation as you build

---

## Next Steps

**Immediate (Day 1):**
1. Read this brief + architecture + epics/stories
2. Set up project tracking (Notion/Linear with BMAD structure)
3. Schedule 5 user interviews (validate problem/solution)
4. Start Phase 0: Implement staging support

**This Week:**
- Complete Week 1 tasks (physics core)
- Write tests for staging, gravity, atmosphere
- Research Falcon 9 parameters

**This Month:**
- Complete Phase 0 (validation <5%)
- Start Phase 1 (vehicle database)
- Recruit 5-10 alpha testers

---

## Appendix: User Research Questions

**For NewSpace engineers (10+ interviews):**
1. Walk me through your current process for preliminary mission design
2. How long does a typical trade study take?
3. What tools do you use? What frustrates you about them?
4. If this tool existed, how would you use it?
5. What would make you switch from your current process?
6. How much would you pay for a tool that saves you 2 days per study?

**For educators (5+ interviews):**
1. How do you teach orbital mechanics?
2. What software do students use?
3. What's the barrier to using STK/GMAT?
4. Would you use a free web-based simulator?

---

**Status:** ✅ Brief Complete  
**Next:** Architecture Document (02-architecture.md)  
**Owner:** Rico + James  
**Review:** Weekly check-in every Sunday
