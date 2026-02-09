# Launch/Landing Simulator - BMAD Plan

**Created:** 2026-02-09  
**Owner:** Rico (@e-cesar9)  
**Status:** Ready to start  
**Timeline:** 6 weeks to MVP

## 🎯 Quick Summary

Building a **Monte-Carlo launch simulator** that doesn't just answer "will it work?" but **"what should we test next?"**

**Key Features:**
- 10K+ probabilistic simulations in <30s
- Parameter sensitivity ranking (Sobol indices)
- Success rate + failure mode analysis
- Interactive UI in existing SpaceX Orbital app

**Why This Matters:**
- No open-source tool like this exists
- Shows systems thinking (not just features)
- Perfect for SpaceX/OpenAI portfolio
- Publishable research quality

---

## 📂 Documents

1. **[01-product-brief.md](./01-product-brief.md)**
   - Problem, users, MVP scope
   - Success metrics, timeline
   - Read this first!

2. **[02-architecture.md](./02-architecture.md)**
   - Technical design
   - Data models, API endpoints
   - Technology choices

3. **[03-epics-stories.md](./03-epics-stories.md)**
   - 29 stories across 7 epics
   - Sprint-by-sprint plan
   - Definition of done

---

## 🚀 How to Start

### Step 1: Review Plan (30 min)
```bash
cd docs/bmad
cat 01-product-brief.md 02-architecture.md 03-epics-stories.md
```

**Decisions needed:**
- ✅ 2D vs 3D? → Start 2D (faster MVP)
- ✅ Sobol vs Morris? → Sobol (accurate)
- ✅ Store results? → Redis 1h TTL

### Step 2: Setup Environment
```bash
# Backend dependencies
cd backend
pip install numpy scipy SALib

# Test installation
python -c "from SALib.analyze import sobol; print('OK')"
```

### Step 3: Start Sprint 1
**Focus:** Physics engine foundation

**First story:** S1.1 Basic 2D Physics Model (5 points)

```bash
# Create physics module
cd backend/app/services
touch physics_engine.py

# Run tests
cd backend
pytest tests/test_physics_engine.py -v
```

---

## 📊 Progress Tracking

### Week 1 (Current)
- [ ] S1.1: Basic 2D Physics Model
- [ ] S1.2: Engine Model with Thrust Variance
- [ ] S1.3: Drag & Atmosphere Model

### Week 2
- [ ] S1.4: Success/Failure Classification
- [ ] S1.5: Validation Against Real Data
- [ ] S2.1: Parameter Distribution Sampling

### Weeks 3-6
- See [03-epics-stories.md](./03-epics-stories.md) for full sprint plan

---

## 🎨 UI Mockup

```
┌────────────────────────────────────────────────┐
│  Launch Simulator                       🚀     │
├────────────────────────────────────────────────┤
│  Run Monte-Carlo simulations to explore       │
│  launch success under uncertainty.             │
│                                                │
│  ┌──────────────────────────────────────┐    │
│  │ Parameters                            │    │
│  │                                       │    │
│  │ Thrust:     [====|=====] 7.5 MN      │    │
│  │ Distribution: [Normal ▼] ±5%         │    │
│  │                                       │    │
│  │ Isp:        [=====|====] 310s        │    │
│  │ Cd:         [==|========] 0.3        │    │
│  │ ... (6 total parameters)             │    │
│  │                                       │    │
│  │ Runs: [10,000]  Seed: [42]          │    │
│  │                                       │    │
│  │ [Reset]        [Run Simulation]      │    │
│  └──────────────────────────────────────┘    │
│                                                │
│  ┌──────────────────────────────────────┐    │
│  │ Results                               │    │
│  │                                       │    │
│  │ Success Rate:  87.3%  ████████░░     │    │
│  │ Mean Altitude: 203 ± 12 km           │    │
│  │                                       │    │
│  │ Most Important Parameters:            │    │
│  │ 1. Thrust variance    ████████ 45%   │    │
│  │ 2. Cd                 ████░░░░ 23%   │    │
│  │ 3. Gimbal delay       ██░░░░░░ 15%   │    │
│  │                                       │    │
│  │ Failure Modes:                        │    │
│  │ • Fuel depletion  8.2%               │    │
│  │ • Altitude miss   3.1%               │    │
│  │ • Structural      1.4%               │    │
│  │                                       │    │
│  │ [View Trajectories]                   │    │
│  └──────────────────────────────────────┘    │
└────────────────────────────────────────────────┘
```

---

## 🧠 Key Technical Decisions

### Physics Model
- **2D vertical ascent** (not full 3D pitch/yaw)
- **RK4 integration** at 0.1s timestep
- **Exponential atmosphere** (NASA standard)
- **Tsiolkovsky rocket equation** for fuel

**Why simplified?**
- 80% of insights, 20% of complexity
- MVP in 6 weeks vs 6 months
- Can expand to 3D in P1

### Monte Carlo
- **10,000 runs** (sweet spot: speed vs accuracy)
- **Latin Hypercube Sampling** (better than random)
- **Multiprocessing** (use all CPU cores)
- **30s target** (fast feedback loop)

### Sensitivity Analysis
- **Sobol indices** (variance-based, gold standard)
- **First-order + Total-order** (captures interactions)
- **Rank top 5 parameters** (actionable insights)

---

## 📈 Success Criteria

### Technical (MVP)
- [x] Plan complete
- [ ] Physics validated against real data (±10%)
- [ ] 10K runs in <30s
- [ ] Sensitivity ranking intuitive
- [ ] UI integrated smoothly

### Strategic (3 months)
- [ ] 500+ simulation runs by users
- [ ] Featured in 1+ blog/paper
- [ ] Included in portfolio for SpaceX application
- [ ] 20+ GitHub stars

---

## 🚨 Risks

| Risk | Mitigation |
|------|------------|
| Physics too hard | Use ChatGPT for equations, validate early |
| Performance too slow | Profile early, optimize hot paths |
| Frontend too complex | Reuse existing components |
| Scope creep | Strict P0/P1, timebox to 6 weeks |

---

## 📚 Resources

### Learning
- [SALib Docs](https://salib.readthedocs.io/) - Sensitivity analysis
- [Rocket Equation](https://en.wikipedia.org/wiki/Tsiolkovsky_rocket_equation)
- [NASA Atmosphere Model](https://www.grc.nasa.gov/www/k-12/airplane/atmosmet.html)

### Validation Data
- SpaceX webcasts (altitude/velocity plots)
- CRS-1 mission telemetry
- Falcon 9 user guide (public)

### Inspiration
- GMAT (NASA)
- Kerbal Space Program
- Academic papers on launch optimization

---

## 🤝 How to Contribute

This is Rico's portfolio project, but feedback welcome:

1. **Review plan** - Spot issues, suggest improvements
2. **Code reviews** - PRs on GitHub
3. **Testing** - Try the simulator, report bugs
4. **Promotion** - Share on Twitter/HN when launched

---

## 📞 Questions?

- **Plan unclear?** → Ask in GitHub Discussions
- **Technical issue?** → Open GitHub Issue
- **Want to collaborate?** → DM @rico3634

---

**Let's ship this! 🚀**

---

_Last updated: 2026-02-09_
