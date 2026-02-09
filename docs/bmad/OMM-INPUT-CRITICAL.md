# 🔴 CRITICAL: OMM Input Support - Tu as raison

**Date:** 2026-02-09  
**Issue:** App supporte seulement TLE input, pas OMM  
**Impact:** BLOQUANT pour NASA-grade quality

---

## PARTIE 1: POURQUOI TU AS RAISON

### ❌ Faiblesse Actuelle

**Code existant:**
```python
# backend/app/services/tle_service.py
def load_tle(self, satellite_id: str, tle_line1: str, tle_line2: str):
    """Load TLE data."""
    satellite = Satrec.twoline2rv(tle_line1, tle_line2)
    # ← PROBLÈME: TLE ONLY!
```

**Ce que ça signifie:**
```
Sources de données possibles:
├── CelesTrak (TLE) ✅ Supporté
├── Space-Track (TLE) ✅ Supporté
├── Space-Track (OMM) ❌ NON SUPPORTÉ ← CRITIQUE
├── NASA CARA (OMM) ❌ NON SUPPORTÉ
├── ESA (OMM) ❌ NON SUPPORTÉ
└── SpaceX (OMM) ❌ NON SUPPORTÉ
```

**Impact:**
- ❌ Limité aux sources TLE uniquement
- ❌ Ne peut pas ingérer OMM de NASA/ESA
- ❌ Ne peut pas recevoir OMM avec covariance
- ❌ Stuck avec format legacy (TLE = années 1960)

---

## PARTIE 2: TLE vs OMM - COMPARAISON TECHNIQUE

### Format TLE (Two-Line Element Set)

**Créé:** 1960s par NORAD  
**Format:** 2 lignes ASCII de 69 caractères

```
1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537
         ↑        ↑         ↑
    Inclination  RAAN   Eccentricity
```

**Contenu:**
- ✅ Mean orbital elements (6 Keplerian elements)
- ✅ Epoch (date/time)
- ✅ NORAD ID
- ❌ **PAS de covariance matrix** (incertitude)
- ❌ **PAS de metadata** (opérateur, maneuver plans)
- ❌ **PAS de state vector** (position/velocity directe)

**Limitations:**
1. **Précision:** ±1-5km (mean elements, pas osculating)
2. **Âge:** Format ancient, pas extensible
3. **Metadata:** Aucune (qui opère? quelle mission?)
4. **Incertitude:** Non quantifiée

---

### Format OMM (Orbit Mean-Elements Message)

**Créé:** 2000s par CCSDS (Consultative Committee for Space Data Systems)  
**Format:** XML ou KVN (Key-Value Notation)

```xml
<omm>
  <header>
    <CREATION_DATE>2026-02-09T15:00:00Z</CREATION_DATE>
    <ORIGINATOR>NASA</ORIGINATOR>
  </header>
  <body>
    <segment>
      <metadata>
        <OBJECT_NAME>ISS (ZARYA)</OBJECT_NAME>
        <OBJECT_ID>25544</OBJECT_ID>
        <CENTER_NAME>EARTH</CENTER_NAME>
        <REF_FRAME>TEME</REF_FRAME>
        <TIME_SYSTEM>UTC</TIME_SYSTEM>
        <MEAN_ELEMENT_THEORY>SGP4</MEAN_ELEMENT_THEORY>
      </metadata>
      <data>
        <meanElements>
          <EPOCH>2026-02-09T15:00:00.000Z</EPOCH>
          <SEMI_MAJOR_AXIS unit="km">6793.366</SEMI_MAJOR_AXIS>
          <ECCENTRICITY>0.0006703</ECCENTRICITY>
          <INCLINATION unit="deg">51.6416</INCLINATION>
          <RA_OF_ASC_NODE unit="deg">247.4627</RA_OF_ASC_NODE>
          <ARG_OF_PERICENTER unit="deg">130.5360</ARG_OF_PERICENTER>
          <MEAN_ANOMALY unit="deg">325.0288</MEAN_ANOMALY>
        </meanElements>
        
        <!-- OPTIONNEL: Covariance Matrix -->
        <covarianceMatrix>
          <COV_REF_FRAME>TEME</COV_REF_FRAME>
          <CX_X unit="m**2">44.6</CX_X>
          <CY_X unit="m**2">-7.2</CY_X>
          <CY_Y unit="m**2">66.6</CY_Y>
          <!-- ... 21 elements total (6x6 symmetric) -->
        </covarianceMatrix>
        
        <!-- OPTIONNEL: User-Defined Parameters -->
        <userDefinedParameters>
          <USER_DEFINED parameter="OPERATOR">NASA</USER_DEFINED>
          <USER_DEFINED parameter="MISSION">ISS</USER_DEFINED>
          <USER_DEFINED parameter="NEXT_MANEUVER">2026-02-15</USER_DEFINED>
        </userDefinedParameters>
      </data>
    </segment>
  </body>
</omm>
```

**Contenu:**
- ✅ Mean orbital elements (comme TLE)
- ✅ Epoch (date/time)
- ✅ NORAD ID + name
- ✅ **Covariance matrix** (incertitude quantifiée!) 🔥
- ✅ **Metadata** (opérateur, mission, etc.)
- ✅ **Extensible** (user-defined parameters)
- ✅ **Units explicites** (km, deg, m²)
- ✅ **Validable** (XML schema)

**Avantages:**
1. **Precision:** Même que TLE MAIS avec incertitude quantifiée
2. **Moderne:** Format standard international
3. **Metadata:** Rich context (operator, mission, plans)
4. **Covariance:** Permet collision probability calculation
5. **Extensible:** Peut ajouter custom fields

---

## PARTIE 3: POURQUOI OMM INPUT EST CRITIQUE

### Use Case 1: NASA Conjunction Data Messages (CDM)

**NASA publie des CDM (Conjunction Data Messages) en OMM format:**

```
Space-Track.org → CDM Public Feed
├── OMM pour satellite 1
├── OMM pour satellite 2
├── Time of Closest Approach (TCA)
├── Miss distance
└── Probability of Collision (Pc)
```

**Si ton app supporte OMM input:**
- ✅ Peut ingérer CDM directement
- ✅ Peut valider Pc calculations
- ✅ Peut afficher covariance (uncertainty ellipsoid)
- ✅ Devient outil de coordination collision avoidance

**Sans OMM input:**
- ❌ Doit convertir OMM → TLE (perd covariance!)
- ❌ Ne peut pas calculer Pc correct
- ❌ Pas d'uncertainty visualization

---

### Use Case 2: Opérateurs Commerciaux

**SpaceX, Planet, etc. publient OMM (pas TLE) pour coordination:**

```
Exemple: SpaceX Starlink maneuver notification
<omm>
  <metadata>
    <OBJECT_NAME>STARLINK-1234</OBJECT_NAME>
    <OPERATOR>SpaceX</OPERATOR>
  </metadata>
  <meanElements>
    <EPOCH>2026-02-09T15:00:00Z</EPOCH>
    <!-- Orbital elements POST-maneuver -->
  </meanElements>
  <userDefinedParameters>
    <USER_DEFINED parameter="MANEUVER_PLANNED">2026-02-10T12:00:00Z</USER_DEFINED>
    <USER_DEFINED parameter="DELTA_V">0.5 m/s</USER_DEFINED>
  </userDefinedParameters>
</omm>
```

**Si ton app supporte OMM input:**
- ✅ Peut ingérer maneuver plans
- ✅ Peut prédire post-maneuver trajectories
- ✅ Peut alerter sur conflicts

**Sans OMM input:**
- ❌ Ne peut pas ingérer ces données
- ❌ Limité aux TLE publics (delayed, no maneuver info)

---

### Use Case 3: High-Accuracy Sources

**Certaines sources publient OMM avec better accuracy:**

```
ESA DISCOS (Database and Information System Characterising Objects in Space)
├── OMM avec covariance matrix
├── Multiple observations fusionnées
├── Accuracy: ±100m (vs ±5km TLE)
└── Update frequency: Every orbit
```

**Si ton app supporte OMM input:**
- ✅ Peut utiliser high-accuracy data
- ✅ Améliore precision à ±100m
- ✅ Professional quality

**Sans OMM input:**
- ❌ Stuck avec TLE ±5km
- ❌ Cannot leverage better data

---

## PARTIE 4: SPICE API + OMM INPUT

### Pourquoi SPICE API aide avec OMM

**SPICE Service (haisamido/spice) supporte OMM input:**

```bash
# API Endpoint
POST /api/spice/omm/propagate

# Input: OMM (XML or JSON)
{
  "omm": {
    "metadata": {...},
    "meanElements": {...},
    "covarianceMatrix": {...}  # ← SPICE peut lire ça!
  },
  "t0": "2026-02-09T15:00:00Z",
  "tf": "2026-02-09T16:00:00Z",
  "step": 60
}

# Output: State vectors avec covariance propagée
{
  "states": [
    {
      "time": "2026-02-09T15:00:00Z",
      "position": {"x": 6678.137, "y": 0, "z": 0},
      "velocity": {"vx": 0, "vy": 7.612, "vz": 0},
      "covariance": [[44.6, -7.2, ...], [...]]  # ← Propagated!
    }
  ]
}
```

**Ce que SPICE apporte:**
1. ✅ **OMM parsing** (XML → internal format)
2. ✅ **Covariance propagation** (pas juste mean elements)
3. ✅ **Multiple input formats** (TLE, OMM, OSM, OPM)
4. ✅ **High-performance** (750K prop/s)

---

## PARTIE 5: PLAN RÉVISÉ - OMM INPUT PRIORITY

### 🔴 OMM Input = P0 (CRITIQUE)

**Nouvelle architecture:**

```python
# backend/app/services/orbital_data_service.py

from enum import Enum
from typing import Union

class OrbitalDataFormat(Enum):
    TLE = "tle"
    OMM = "omm"
    OPM = "opm"  # Orbit Parameter Message (state vectors)

class OrbitalDataService:
    """Unified service for TLE, OMM, OPM input."""
    
    async def ingest_data(
        self,
        data: Union[TLEData, OMMData, OPMData],
        format: OrbitalDataFormat
    ) -> SatelliteOrbit:
        """
        Ingest orbital data in any format.
        
        Converts to internal representation for propagation.
        """
        if format == OrbitalDataFormat.TLE:
            return self._ingest_tle(data)
        elif format == OrbitalDataFormat.OMM:
            return self._ingest_omm(data)  # ← NEW!
        elif format == OrbitalDataFormat.OPM:
            return self._ingest_opm(data)  # ← NEW!
    
    def _ingest_omm(self, omm: OMMData) -> SatelliteOrbit:
        """Parse OMM and extract orbital elements."""
        # Parse XML or KVN
        parsed = self._parse_omm(omm.content, omm.format)
        
        # Extract mean elements
        orbit = SatelliteOrbit(
            satellite_id=parsed.metadata.OBJECT_ID,
            epoch=parsed.meanElements.EPOCH,
            semi_major_axis=parsed.meanElements.SEMI_MAJOR_AXIS,
            eccentricity=parsed.meanElements.ECCENTRICITY,
            inclination=parsed.meanElements.INCLINATION,
            raan=parsed.meanElements.RA_OF_ASC_NODE,
            arg_perigee=parsed.meanElements.ARG_OF_PERICENTER,
            mean_anomaly=parsed.meanElements.MEAN_ANOMALY
        )
        
        # Extract covariance if present
        if parsed.covarianceMatrix:
            orbit.covariance = self._parse_covariance_matrix(
                parsed.covarianceMatrix
            )
        
        # Extract metadata
        if parsed.userDefinedParameters:
            orbit.metadata = self._parse_metadata(
                parsed.userDefinedParameters
            )
        
        return orbit
```

---

### Sprint Planning RÉVISÉ

**Week 1: OMM Input Foundation** (NOUVELLE PRIORITÉ)

**S1.1: OMM Parser (XML + KVN)** (5 points)
```python
# Skills: architecture (data parsing), code-quality (validation)

from lxml import etree
import xmlschema

class OMMParser:
    """Parse OMM XML and KVN formats."""
    
    def __init__(self):
        # Load CCSDS OMM schema for validation
        self.schema = xmlschema.XMLSchema('ccsds_omm_v2.0.xsd')
    
    def parse_xml(self, xml_content: str) -> OMMData:
        """Parse OMM XML with schema validation."""
        # Validate against CCSDS schema
        if not self.schema.is_valid(xml_content):
            errors = self.schema.validate(xml_content)
            raise ValidationError(f"OMM XML invalid: {errors}")
        
        # Parse
        tree = etree.fromstring(xml_content.encode())
        
        # Extract metadata
        metadata = OMMMetadata(
            OBJECT_NAME=tree.find('.//OBJECT_NAME').text,
            OBJECT_ID=tree.find('.//OBJECT_ID').text,
            CENTER_NAME=tree.find('.//CENTER_NAME').text,
            REF_FRAME=tree.find('.//REF_FRAME').text,
            TIME_SYSTEM=tree.find('.//TIME_SYSTEM').text
        )
        
        # Extract mean elements
        mean_elements = OMMMeanElements(
            EPOCH=datetime.fromisoformat(tree.find('.//EPOCH').text),
            SEMI_MAJOR_AXIS=float(tree.find('.//SEMI_MAJOR_AXIS').text),
            ECCENTRICITY=float(tree.find('.//ECCENTRICITY').text),
            INCLINATION=float(tree.find('.//INCLINATION').text),
            RA_OF_ASC_NODE=float(tree.find('.//RA_OF_ASC_NODE').text),
            ARG_OF_PERICENTER=float(tree.find('.//ARG_OF_PERICENTER').text),
            MEAN_ANOMALY=float(tree.find('.//MEAN_ANOMALY').text)
        )
        
        # Extract covariance if present
        covariance = None
        cov_node = tree.find('.//covarianceMatrix')
        if cov_node is not None:
            covariance = self._parse_covariance_matrix(cov_node)
        
        return OMMData(
            metadata=metadata,
            mean_elements=mean_elements,
            covariance=covariance
        )
    
    def parse_kvn(self, kvn_content: str) -> OMMData:
        """Parse OMM KVN format."""
        lines = kvn_content.strip().split('\n')
        data = {}
        
        for line in lines:
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            data[key.strip()] = value.strip()
        
        # Build OMMData from key-value pairs
        # ... (similar to XML but simpler)
```

**Acceptance Criteria:**
- [ ] Parse OMM XML (CCSDS 2.0 compliant)
- [ ] Parse OMM KVN
- [ ] Validate against CCSDS schema
- [ ] Extract covariance matrix (if present)
- [ ] Extract user-defined parameters
- [ ] Unit tests: Valid OMM parses correctly
- [ ] Unit tests: Invalid OMM raises ValidationError

---

**S1.2: OMM → Propagation Engine** (3 points)
```python
# Skills: architecture (data transformation), code-quality

class OrbitalDataService:
    async def ingest_omm(
        self,
        omm: OMMData,
        source: str = "user_upload"
    ) -> str:
        """
        Ingest OMM data into propagation engine.
        
        Returns:
            satellite_id (loaded and ready for propagation)
        """
        # Parse OMM
        parsed = omm_parser.parse(omm.content, omm.format)
        
        # Convert to internal format
        orbit = SatelliteOrbit(
            satellite_id=parsed.metadata.OBJECT_ID,
            name=parsed.metadata.OBJECT_NAME,
            epoch=parsed.mean_elements.EPOCH,
            # ... orbital elements ...
            covariance=parsed.covariance,  # ← NEW!
            metadata={
                "source": source,
                "originator": parsed.header.ORIGINATOR,
                "creation_date": parsed.header.CREATION_DATE
            }
        )
        
        # Load into propagation engine
        # If SPICE available, use SPICE (supports covariance)
        # Otherwise, SGP4 (mean elements only)
        if spice_client.available and orbit.covariance:
            await spice_client.load_omm(orbit)
        else:
            # Fallback: Convert to TLE for SGP4
            tle = self._omm_to_tle(orbit)
            orbital_engine.load_tle(orbit.satellite_id, tle.line1, tle.line2)
        
        logger.info("OMM ingested", sat_id=orbit.satellite_id, source=source)
        return orbit.satellite_id
```

---

**S1.3: API Endpoint - POST /satellites/omm** (3 points)
```python
# Skills: architecture (API design), code-quality (error handling)

@router.post("/satellites/omm")
@limiter.limit("10/minute")
async def upload_omm(
    request: Request,
    file: UploadFile = File(...),
    format: Literal['xml', 'kvn'] = Form('xml'),
    validate: bool = Form(True)
):
    """
    Upload satellite orbital data in OMM format.
    
    Accepts:
    - OMM XML (CCSDS 2.0)
    - OMM KVN
    
    Returns:
    - satellite_id (ready for queries)
    """
    # Read file
    content = await file.read()
    
    try:
        # Parse OMM
        omm = OMMData(content=content.decode(), format=format)
        parsed = omm_parser.parse(omm.content, format)
        
        # Validate if requested
        if validate:
            omm_validator.validate(parsed)
        
        # Ingest into engine
        sat_id = await orbital_data_service.ingest_omm(
            omm,
            source="user_upload"
        )
        
        return {
            "status": "success",
            "satellite_id": sat_id,
            "name": parsed.metadata.OBJECT_NAME,
            "epoch": parsed.mean_elements.EPOCH.isoformat(),
            "has_covariance": parsed.covariance is not None,
            "message": "OMM ingested successfully"
        }
        
    except ValidationError as e:
        raise HTTPException(400, f"OMM validation failed: {str(e)}")
    except Exception as e:
        logger.error("OMM upload failed", error=str(e))
        raise HTTPException(500, f"OMM processing failed: {str(e)}")
```

---

**S1.4: SPICE Client - OMM Support** (5 points)
```python
# Skills: architecture (integration), microservices (external API)

class SpiceClient:
    """Client for SPICE API with OMM support."""
    
    async def load_omm(self, orbit: SatelliteOrbit) -> bool:
        """Load OMM into SPICE for propagation."""
        # Convert internal format → SPICE OMM JSON
        omm_json = {
            "metadata": {
                "OBJECT_NAME": orbit.name,
                "OBJECT_ID": orbit.satellite_id,
                "CENTER_NAME": "EARTH",
                "REF_FRAME": "TEME",
                "TIME_SYSTEM": "UTC"
            },
            "meanElements": {
                "EPOCH": orbit.epoch.isoformat(),
                "SEMI_MAJOR_AXIS": orbit.semi_major_axis,
                "ECCENTRICITY": orbit.eccentricity,
                "INCLINATION": orbit.inclination,
                "RA_OF_ASC_NODE": orbit.raan,
                "ARG_OF_PERICENTER": orbit.arg_perigee,
                "MEAN_ANOMALY": orbit.mean_anomaly
            }
        }
        
        # Add covariance if present
        if orbit.covariance:
            omm_json["covarianceMatrix"] = {
                "COV_REF_FRAME": "TEME",
                "CX_X": orbit.covariance[0][0],
                "CY_X": orbit.covariance[1][0],
                "CY_Y": orbit.covariance[1][1],
                # ... full 6x6 matrix ...
            }
        
        # Send to SPICE
        response = await self.client.post(
            "/api/spice/omm/load",
            json={"omm": omm_json}
        )
        
        if response.status_code != 200:
            raise Exception(f"SPICE load failed: {response.text}")
        
        return True
    
    async def propagate_with_covariance(
        self,
        sat_id: str,
        epoch: datetime
    ) -> Tuple[SatellitePosition, CovarianceMatrix]:
        """Propagate with covariance propagation."""
        response = await self.client.post(
            "/api/spice/omm/propagate",
            json={
                "satellite_id": sat_id,
                "epoch": epoch.isoformat(),
                "include_covariance": True
            }
        )
        
        data = response.json()
        
        position = SatellitePosition(
            satellite_id=sat_id,
            timestamp=epoch,
            x=data["position"]["x"],
            y=data["position"]["y"],
            z=data["position"]["z"],
            # ...
        )
        
        covariance = CovarianceMatrix(
            data=np.array(data["covariance"])
        )
        
        return position, covariance
```

---

## RÉSUMÉ EXÉCUTIF

### Tu as raison: OMM Input = Critical

**Problème identifié:**
- ✅ App actuelle: TLE input only
- ❌ Faiblesse: Cannot ingest OMM (modern format)
- ❌ Impact: Limited to TLE sources only

**Solution:**
- ✅ OMM Input support (XML + KVN)
- ✅ Covariance matrix parsing
- ✅ SPICE API pour propagation avec covariance
- ✅ API endpoint: POST /satellites/omm

**Benefits:**
1. ✅ Ingest NASA CDM (conjunction data)
2. ✅ Ingest operator OMM (SpaceX, Planet, etc.)
3. ✅ Support high-accuracy sources (ESA DISCOS)
4. ✅ Covariance propagation (uncertainty tracking)
5. ✅ Modern format (2000s vs 1960s)

---

## PLAN RÉVISÉ - PRIORITY CORRECTE

**Week 1: OMM Input (CRITIQUE)** ← NEW PRIORITY
- S1.1: OMM Parser (XML + KVN) (5pts)
- S1.2: OMM → Propagation Engine (3pts)
- S1.3: API Endpoint POST /satellites/omm (3pts)
- S1.4: SPICE Client OMM Support (5pts)

**Week 2-5: Comme prévu** (Performance, Quality, Export)

---

**Timeline: 5 semaines MAIS Week 1 réorganisée**

**Question:** C'était bien ça ton point? OMM INPUT (pas juste export)? 🎯
