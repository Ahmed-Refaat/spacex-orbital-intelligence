"""
OMM (Orbit Mean-Elements Message) data models.

Story 1.3: Form Input Validation (P1-7)
"""
from pydantic import BaseModel, Field, validator
from typing import Literal


class OMMUploadForm(BaseModel):
    """
    Validated form data for OMM file upload.
    
    Security constraints:
    - format: Only 'xml' or 'json' allowed
    - source: Alphanumeric + underscore/hyphen only, max 100 chars
    """
    format: Literal['xml', 'json'] = Field(
        description="OMM format (xml or json)"
    )
    
    source: str = Field(
        default="user_upload",
        max_length=100,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Data source identifier (alphanumeric, underscore, hyphen only)"
    )
    
    @validator('source')
    def sanitize_source(cls, v: str) -> str:
        """
        Sanitize source field.
        
        - Strip whitespace
        - Convert to lowercase for consistency
        - Reject empty strings
        """
        v = v.strip()
        
        if not v:
            raise ValueError("source cannot be empty")
        
        return v.lower()
    
    class Config:
        """Pydantic config."""
        # Strict validation
        str_strip_whitespace = True
        
        # Example for docs
        schema_extra = {
            "example": {
                "format": "xml",
                "source": "nasa_cdm_2024"
            }
        }
