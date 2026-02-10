"""
Local TLE file loader - Ultimate fallback.

When all API sources fail, load from static TLE files.
"""
import json
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()

TLE_DATA_DIR = Path(__file__).parent.parent / "data"


class LocalTLELoader:
    """Load TLE data from local JSON files."""
    
    @staticmethod
    def load_starlink() -> dict[str, tuple[str, str, str]]:
        """
        Load Starlink TLE from local file.
        
        Returns:
            Dict mapping NORAD ID to (name, line1, line2)
        """
        file_path = TLE_DATA_DIR / "starlink_tle.json"
        
        if not file_path.exists():
            logger.warning("Local Starlink TLE file not found", path=str(file_path))
            return {}
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            result = {}
            for sat in data:
                try:
                    norad_id = str(sat.get("NORAD_CAT_ID", "")).strip()
                    name = sat.get("OBJECT_NAME", f"SAT-{norad_id}")
                    line1 = sat.get("TLE_LINE1", "")
                    line2 = sat.get("TLE_LINE2", "")
                    
                    if norad_id and line1 and line2:
                        result[norad_id] = (name, line1, line2)
                except Exception as e:
                    logger.warning("Failed to parse satellite from local file", error=str(e))
                    continue
            
            logger.info(
                "Loaded TLE data from local file",
                count=len(result),
                source="local_file"
            )
            return result
            
        except Exception as e:
            logger.error("Failed to load local TLE file", path=str(file_path), error=str(e))
            return {}
    
    @staticmethod
    def load_stations() -> dict[str, tuple[str, str, str]]:
        """Load space stations TLE from local file."""
        file_path = TLE_DATA_DIR / "stations_tle.json"
        
        if not file_path.exists():
            logger.warning("Local stations TLE file not found", path=str(file_path))
            return {}
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            result = {}
            for sat in data:
                try:
                    norad_id = str(sat.get("NORAD_CAT_ID", "")).strip()
                    name = sat.get("OBJECT_NAME", f"SAT-{norad_id}")
                    line1 = sat.get("TLE_LINE1", "")
                    line2 = sat.get("TLE_LINE2", "")
                    
                    if norad_id and line1 and line2:
                        result[norad_id] = (name, line1, line2)
                except Exception:
                    continue
            
            logger.info("Loaded stations from local file", count=len(result), source="local_file")
            return result
            
        except Exception as e:
            logger.error("Failed to load local stations file", path=str(file_path), error=str(e))
            return {}


# Global instance
local_tle_loader = LocalTLELoader()
