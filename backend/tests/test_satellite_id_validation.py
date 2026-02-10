"""
Test strict satellite ID validation.

Security: Prevent injection attacks via malformed satellite IDs.
"""
import pytest
from fastapi import HTTPException
from app.api.satellites import validate_satellite_id


def test_valid_satellite_id():
    """Accept valid NORAD IDs (1-99999)."""
    assert validate_satellite_id("1") == "1"
    assert validate_satellite_id("12345") == "12345"
    assert validate_satellite_id("99999") == "99999"


def test_reject_invalid_satellite_id():
    """Reject IDs with invalid format."""
    # Too long
    with pytest.raises(HTTPException) as exc:
        validate_satellite_id("123456")
    assert exc.value.status_code == 400
    
    # Contains letters
    with pytest.raises(HTTPException) as exc:
        validate_satellite_id("123abc")
    assert exc.value.status_code == 400
    
    # Special characters (injection attempt)
    with pytest.raises(HTTPException) as exc:
        validate_satellite_id("123; DROP TABLE")
    assert exc.value.status_code == 400
    
    # Empty
    with pytest.raises(HTTPException) as exc:
        validate_satellite_id("")
    assert exc.value.status_code == 400
    
    # SQL injection attempt
    with pytest.raises(HTTPException) as exc:
        validate_satellite_id("1' OR '1'='1")
    assert exc.value.status_code == 400


def test_edge_cases():
    """Test boundary values."""
    # Leading zeros are ok
    assert validate_satellite_id("00001") == "00001"
    
    # But not 6+ digits
    with pytest.raises(HTTPException):
        validate_satellite_id("000001")
