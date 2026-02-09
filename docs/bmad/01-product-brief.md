# Product Brief - Launch/Landing Simulator

**Created:** 2026-02-09  
**Owner:** Rico  
**Status:** Planning

## Problem Statement

SpaceX and the Mars mission community lack publicly available tools to:
1. **Explore launch/landing parameter sensitivities** probabilistically
2. **Identify which uncertainties matter most** for mission success
3. **Suggest optimal next test parameters** based on simulation results
4. **Visualize failure modes** across thousands of scenarios

Current internal tools (if they exist) are:
- Proprietary and inaccessible
- Not probabilistic (single-run focused)
- Don't expose decision-making insights

## Target Users

### Primary
- **Engineering students & researchers** studying orbital mechanics
- **NewSpace startups** prototyping launch/landing systems
- **Aerospace enthusiasts** wanting to understand real constraints

### Secondary
- **SpaceX recruiters** evaluating technical depth of candidates
- **Conference attendees** (IAC, AIAA, etc.) seeking demos
- **Open-source community** building on the platform

## Core Value Proposition

> A Monte-Carlo launch/landing simulator that doesn't just show "will it work?" but answers "what should we test next?"

**Differentiators:**
1. **Probabilistic** - 10K+ runs, not 1 trajectory
2. **Decision-focused** - Ranks parameters by impact
3. **Open & accessible** - No proprietary barriers
4. **Integrated** - Lives in existing orbital intelligence platform

## MVP Scope (P0 - Ship in 6 weeks)

### Must Have (P0)
- [ ] **Backend Monte-Carlo engine**
  - 6-DOF physics (simplified but correct)
  - Configurable parameter distributions
  - 10,000 runs in <30 seconds
  - Success/failure classification
  
- [ ] **Parameter sensitivity analysis**
  - Sobol indices calculation
  - Top 5 "most important" parameters
  - Failure mode clustering
  
- [ ] **Frontend UI in Simulation tab**
  - Parameter sliders with distribution controls
  - "Run Simulation" button
  - Results dashboard: success rate, sensitivity chart
  - Trajectory visualization (sample paths)
  
- [ ] **Launch scenario only** (defer landing to P1)
  - From surface to orbit insertion
  - Simplified atmosphere model
  - Engine thrust/gimbal parameters

### Nice to Have (P1 - Post-MVP)
- [ ] Landing simulation (orbital → surface)
- [ ] Full 3D CFD atmosphere model
- [ ] Multi-stage separation logic
- [ ] Recommendation engine ("test thrust variance next")
- [ ] Export results to CSV/JSON

### Out of Scope (P2)
- Real-time hardware-in-loop simulation
- Multi-vehicle scenarios (booster + ship)
- Propellant sloshing dynamics
- Advanced thermal modeling

## Success Metrics

### Usage (3 months post-launch)
- 500+ simulation runs by unique users
- 20+ GitHub stars on repo
- 3+ mentions on HN/Reddit/Twitter

### Quality
- <1% numerical instability rate
- <5% false positive failures
- >90% test coverage on physics engine

### Strategic
- Featured in 1+ technical blog/paper
- Included in 2+ portfolio sites of team
- 1+ conference demo submission

## Constraints

### Technical
- Must run in browser or lightweight backend (no GPU required)
- Max 30s per 10K simulation runs
- Must integrate with existing React/FastAPI stack

### Timeline
- MVP: 6 weeks
- First demo-ready version: 4 weeks
- Blog post/launch: Week 7

### Budget
- $0 - fully open-source
- Existing infrastructure (Vercel/Railway)

## Timeline

| Week | Milestone |
|------|-----------|
| 1-2  | Backend physics engine + Monte-Carlo runner |
| 3-4  | Sensitivity analysis + parameter ranking |
| 5    | Frontend UI + integration |
| 6    | Testing, docs, polish |
| 7    | Blog post, demo video, HN launch |

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Physics too complex to implement quickly | Medium | High | Start with simplified 2D vertical ascent, expand later |
| Monte-Carlo too slow in browser | Medium | Medium | Run on backend, stream results via WebSocket |
| User engagement low | Medium | Medium | Launch with compelling demo video + real scenario |
| Accuracy questioned | Low | High | Document simplifications clearly, cite sources |

## Open Questions

1. **2D vs 3D simulation for MVP?** → Lean 2D vertical for speed, add 3D in P1
2. **Which launch vehicle to model?** → Falcon 9 (public data) or generic "Starship-like"?
3. **Parameter distributions - who defines?** → Provide defaults, allow user override
4. **Sensitivity method?** → Sobol indices (gold standard) or simpler variance-based?

**Decision needed by:** End of week 1

---

## Appendix: Prior Art

- **Kerbal Space Program** - Game, not decision-focused
- **GMAT (NASA)** - Powerful but complex, no probabilistic mode
- **Academic papers** - Theory-heavy, no interactive tool
- **Internal SpaceX tools** - Unknown, likely proprietary

**Gap:** No open, decision-oriented, probabilistic simulator exists publicly.
