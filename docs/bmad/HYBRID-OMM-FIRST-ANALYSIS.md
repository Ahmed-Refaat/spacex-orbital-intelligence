# Hybrid OMM-First Architecture Analysis

**Date:** 2026-02-09  
**Proposition:** OMM as primary source, TLE as fallback, SPICE as optional service  
**Context:** Open source orbital intelligence platform

---

## 🎯 Architecture Proposée

### Data Source Priority

```
Priority 1: OMM (Orbit Mean-Elements Message)
   ↓ (if available)
SPICE Propagation (high-precision + covariance)
   ↓ (if SPICE unavailable or no OMM)
Priority 2: TLE (Two-Line Elements)
   ↓
SGP4 Propagation (standard precision)
```

### Flow Diagram

```
┌─────────────────────────────────────────┐
│  Data Ingestion                         │
│  ┌─────────────┐    ┌─────────────┐   │
│  │ OMM Upload  │    │ TLE Import  │   │
│  │ (User/API)  │    │ (Space-Tr)  │   │
│  └──────┬──────┘    └──────┬──────┘   │
└─────────┼──────────────────┼───────────┘
          │                  │
          ▼                  ▼
  ┌──────────────────────────────────┐
  │  Unified Satellite Registry      │
  │  {                               │
  │    satellite_id: "25544",        │
  │    data_sources: {               │
  │      omm: {...} (if available),  │
  │      tle: {...} (always),        │
  │    },                            │
  │    priority: "omm" | "tle"       │
  │  }                               │
  └──────────────┬───────────────────┘
                 │
       ┌─────────┴─────────┐
       │                   │
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ SPICE Engine │    │ SGP4 Engine  │
│ (optional)   │    │ (always)     │
│              │    │              │
│ - OMM data   │    │ - TLE data   │
│ - Covariance │    │ - Fast bulk  │
│ - High-prec  │    │ - Reliable   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 │
                 ▼
       ┌─────────────────┐
       │  Propagation    │
       │  Results        │
       │  + Metadata     │
       └─────────────────┘
```

---

## 📊 Disponibilité Données OMM

### Réalité du Marché

**Sources OMM Publiques:**

#### 1. Space-Track.org (18th Space Control Squadron)
- **TLE:** ✅ ~30,000 satellites (bulk, daily updates)
- **CDM:** ✅ High-risk conjunctions with covariance (événementiel)
- **OMM:** ⚠️ Limité (assets critiques seulement)

**Exemples disponibles:**
- ISS (International Space Station)
- TDRS (Tracking & Data Relay Satellites)
- High-value NASA science missions
- **Estimate:** ~100-200 satellites avec OMM public

#### 2. NOAA (Weather Satellites)
- GOES constellation
- JPSS series
- **Estimate:** ~20 satellites

#### 3. ESA (European Space Agency)
- Sentinel constellation (Earth observation)
- Galileo (navigation)
- **Estimate:** ~30 satellites

#### 4. Commercial Operators
- SpaceX Starlink: ❌ Proprietary (not public)
- OneWeb: ❌ Internal use only
- Planet Labs: ❌ Proprietary

**Total Public OMM:** ~150-250 satellites (vs 30,000 TLE)

---

## 🔢 Coverage Analysis

### Data Availability Breakdown

```
Total tracked satellites: ~30,000

TLE availability:
├─ 30,000 satellites (100%)
└─ Updated daily (reliable)

OMM availability:
├─ 150-250 satellites (~0.8%)
├─ Government/critical assets only
└─ Update frequency: varies (days to weeks)

Coverage:
├─ OMM-only coverage: 0.8%
├─ TLE fallback needed: 99.2%
└─ Conclusion: TLE CANNOT be replaced
```

**Reality Check:** OMM ne peut PAS être la source primaire pour bulk analysis.

---

## 💡 Revised Architecture: Dual-Track

### Realistic Approach

```
┌─────────────────────────────────────────────┐
│  Track 1: Bulk Analysis (99% of satellites) │
│  ┌─────────────────────────────────┐        │
│  │  TLE → SGP4 → Analysis          │        │
│  │  30K satellites                 │        │
│  │  Fast, reliable, always works   │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Track 2: High-Precision (1% of satellites) │
│  ┌─────────────────────────────────┐        │
│  │  OMM → SPICE → Analysis         │        │
│  │  ~200 satellites                │        │
│  │  High-precision + uncertainty   │        │
│  │  Optional service (SPICE)       │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘
```

**Key Insight:** OMM = premium feature pour subset, NOT replacement for TLE.

---

## 🎯 Use Case Mapping

### Scenario 1: Bulk Constellation Analysis

**Need:** Track all Starlink satellites (5,000+)

**Data Available:**
- TLE: ✅ All 5,000
- OMM: ❌ None (SpaceX proprietary)

**Solution:** TLE/SGP4 only
- SPICE: Not applicable
- OMM: Not available

**Verdict:** TLE irreplaceable for this use case

---

### Scenario 2: ISS Collision Avoidance

**Need:** High-precision ISS tracking + uncertainty

**Data Available:**
- TLE: ✅ Available (daily)
- OMM: ✅ Available (NASA publishes)

**Solution:** OMM → SPICE (high-precision)
- Covariance: ✅ Available
- Uncertainty: ±100m (vs ±10km TLE)
- Fallback: TLE/SGP4 if SPICE down

**Verdict:** OMM adds significant value here

---

### Scenario 3: CubeSat Tracking (University)

**Need:** Track custom CubeSat

**Data Available:**
- TLE: ✅ Available (Space-Track)
- OMM: ⚠️ Maybe (if operator provides)

**Solution:** 
- Default: TLE/SGP4
- If operator uploads OMM: SPICE
- Graceful upgrade path

**Verdict:** Hybrid approach valuable

---

### Scenario 4: Real-time Conjunction Screening

**Need:** Screen 30K satellites for close approaches

**Data Available:**
- TLE: ✅ All satellites
- OMM: ✅ ~200 critical assets

**Solution:**
- Bulk screening: TLE/SGP4 (fast)
- High-risk pairs: OMM/SPICE (precise)
- Hybrid approach maximizes coverage + precision

**Verdict:** Dual-track optimal

---

## 🏗️ Hybrid Architecture Design

### Satellite Data Model

```python
@dataclass
class SatelliteDataSources:
    """Unified satellite data registry."""
    
    satellite_id: str  # NORAD catalog number
    name: str
    
    # TLE data (always present)
    tle: TLEData
    tle_epoch: datetime
    tle_source: str = "space-track.org"
    
    # OMM data (optional, high-precision)
    omm: Optional[OMMData] = None
    omm_epoch: Optional[datetime] = None
    omm_source: Optional[str] = None
    has_covariance: bool = False
    
    # Data priority
    @property
    def preferred_source(self) -> Literal["omm", "tle"]:
        """Determine which data source to use."""
        if self.omm is None:
            return "tle"
        
        # Use OMM if recent (< 7 days old)
        if self.omm_epoch:
            age = datetime.utcnow() - self.omm_epoch
            if age.days < 7:
                return "omm"
        
        # Fallback to TLE (more frequently updated)
        return "tle"
```

### Propagation Router

```python
class HybridPropagationEngine:
    """Route propagation to SPICE (OMM) or SGP4 (TLE)."""
    
    def __init__(self):
        self.sgp4_engine = SGP4Engine()  # Always available
        self.spice_client = SPICEClient()  # Optional service
        self.spice_available = False
    
    async def propagate(
        self,
        satellite_id: str,
        epoch: datetime,
        include_uncertainty: bool = False
    ) -> PropagationResult:
        """
        Smart propagation routing.
        
        Priority:
        1. OMM + SPICE (if available and recent)
        2. TLE + SGP4 (reliable fallback)
        """
        # Get satellite data
        sat_data = await self.get_satellite_data(satellite_id)
        
        # Check SPICE availability
        if not self.spice_available:
            self.spice_available = await self.spice_client.health_check()
        
        # Route 1: OMM via SPICE (high-precision)
        if (
            sat_data.preferred_source == "omm" 
            and self.spice_available
        ):
            try:
                return await self.spice_client.propagate_omm(
                    satellite_id,
                    epoch,
                    include_covariance=include_uncertainty
                )
            except SPICEError as e:
                logger.warning(
                    "SPICE propagation failed, falling back to SGP4",
                    satellite_id=satellite_id,
                    error=str(e)
                )
        
        # Route 2: TLE via SGP4 (reliable fallback)
        result = self.sgp4_engine.propagate(satellite_id, epoch)
        
        if include_uncertainty and sat_data.preferred_source == "omm":
            result.metadata["warning"] = (
                "Uncertainty requested but SPICE unavailable. "
                "Using TLE/SGP4 (no covariance)."
            )
        
        return result
```

---

## 📊 Performance & Complexity Analysis

### Performance Comparison

| Metric | TLE/SGP4 | OMM/SPICE |
|--------|----------|-----------|
| **Propagation Speed** | ~10K/sec | ~750K/sec |
| **Startup Time** | <1ms | ~100ms (kernel load) |
| **Accuracy** | ±1-10 km | ±0.1-1 km |
| **Uncertainty** | ❌ None | ✅ Covariance |
| **Data Coverage** | 30K sats | ~200 sats |
| **Update Frequency** | Daily | Variable |

### Complexity Cost

| Component | Complexity | Maintenance |
|-----------|------------|-------------|
| **TLE/SGP4 Only** | 🟢 Low | 🟢 Low |
| **+ ANISE** | 🟡 Medium | 🟡 Medium |
| **+ SPICE (optional)** | 🟡 Medium | 🟡 Medium |
| **OMM-First Hybrid** | 🟠 High | 🟠 High |

**Hybrid Overhead:**
- Data source priority logic
- SPICE health monitoring
- Graceful degradation handling
- Dual data ingestion pipelines
- Testing both code paths

---

## 🎯 Pertinence Analysis

### ✅ Arguments POUR Hybrid OMM-First

**1. Future-Proof Architecture**
- More operators may publish OMM in future
- System ready to leverage better data
- Smooth upgrade path for users

**2. Best of Both Worlds**
- High-precision when available (OMM/SPICE)
- Reliable coverage always (TLE/SGP4)
- No single point of failure

**3. Professional Feature Set**
- Uncertainty tracking (when available)
- CCSDS compliance
- Supports operator uploads

**4. Differentiation**
- Most open source tools: TLE-only
- Yours: TLE + OMM hybrid
- Unique value proposition

**5. Educational Value**
- Demonstrates real-world complexity
- Production-grade architecture
- Multiple data source handling

---

### ❌ Arguments CONTRE Hybrid OMM-First

**1. Limited Real-World Impact**
- 0.8% coverage with OMM (200 / 30K)
- 99.2% of queries use TLE anyway
- High complexity for marginal coverage

**2. External Dependency Risk**
- SPICE service (not your code)
- If haisamido/spice disappears → features break
- Maintenance burden

**3. Deployment Complexity**
- Docker-compose (multi-container)
- SPICE health monitoring
- Network between services
- Harder for contributors to run

**4. Development Time**
- 5-7 days vs 0 days (TLE-only)
- Testing both code paths
- Documentation overhead

**5. Questionable ROI (Open Source Context)**
- Portfolio value: TLE + viz already impressive
- OMM adds complexity > visible value
- Deployment difficulty may discourage contributors

---

## 💰 Value vs Effort Matrix

```
               High Value
                    ▲
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    │   OMM for     │   TLE Bulk    │
    │   ISS-class   │   Analysis    │  ← SWEET SPOT
    │   (limited)   │   (30K sats)  │
    │               │               │
    ├───────────────┼───────────────┤
    │               │               │
    │   OMM-First   │   ANISE       │
    │   Hybrid      │   Planetary   │
    │   (complex)   │   (modern)    │
    │               │               │
    └───────────────┼───────────────┘
                    │
                Low Value
               Low Effort ──────────▶ High Effort
```

---

## 🎯 Final Verdict

### ⚠️ Mixed Recommendation

**Pertinence Technique: ⭐⭐⭐ (Solid)**
- Architecture is sound
- Professional design
- Best-of-both-worlds approach

**Pertinence Pratique: ⭐⭐ (Questionable)**
- 99.2% of data uses TLE anyway
- External SPICE dependency
- High complexity for limited coverage

**Pertinence Open Source: ⭐ (Low)**
- Deployment complexity discourages contributors
- External service dependency
- Maintenance burden

---

## 🔄 Alternative Recommendation

### Option 2B: ANISE + Optional OMM

**Better Hybrid:**
```
Priority 1: TLE/SGP4 (always, 30K satellites)
            +
            ANISE (planetary ephemeris, self-contained)
            ↓
Priority 2: OMM/SPICE (optional docker-compose profile)
            ↓
            Document as "advanced deployment"
```

**docker-compose.yml:**
```yaml
services:
  backend:
    # Core: TLE/SGP4 + ANISE
    image: orbital-intelligence:latest
  
  # Optional: Enable OMM support
  spice:
    image: haisamido/spice:latest
    profiles: ["omm"]  # Optional profile
```

**Deployment Options:**
```bash
# Basic: TLE only
docker-compose up

# Advanced: TLE + OMM support
docker-compose --profile omm up
```

**Advantages:**
- ✅ Simple default (no SPICE)
- ✅ Advanced users can enable OMM
- ✅ Self-contained core
- ✅ Optional complexity

---

## 📝 Conclusion

### Direct Answer: Pertinence?

**Pour "Replace TLE by OMM":** ❌ **Not feasible**
- OMM covers only 0.8% of satellites
- TLE is irreplaceable for bulk analysis

**Pour "OMM-First Hybrid with TLE backup":** ⚠️ **Technically sound, practically questionable**
- ✅ Architecture is good
- ✅ Handles both data sources well
- ❌ Limited real-world coverage (0.8%)
- ❌ High complexity for open source project
- ❌ External dependency (SPICE)

**Better Alternative: ANISE + Optional OMM**
- ⭐⭐⭐ Core: TLE/SGP4 + ANISE (self-contained)
- ⭐ Advanced: OMM via SPICE (optional docker profile)
- Best of both worlds: simple default, advanced option

---

## 🎯 Recommendation Finale

### Ship This Instead:

**Phase 1: Core + ANISE (4-5 jours)**
- ✅ TLE/SGP4 (30K satellites)
- ✅ ANISE planetary (Sun/Moon/Earth)
- ✅ Ground station AER
- ✅ Self-contained deployment

**Phase 2: Optional OMM Profile (2-3 jours)**
- ✅ Docker-compose profile for SPICE
- ✅ OMM upload (if SPICE enabled)
- ✅ Document as "advanced feature"
- ✅ Main deployment stays simple

**Result:**
- Simple for most users (TLE + ANISE)
- Advanced for power users (+ OMM/SPICE)
- No forced external dependency
- Clean architecture

---

**Rico: Cette approche fait plus sens?** 💰

Simple par défaut, OMM optionnel pour ceux qui veulent.
