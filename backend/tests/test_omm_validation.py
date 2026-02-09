"""
Tests for OMM upload form validation.

Story 1.3: Form Input Validation (P1-7)
"""
import pytest
from pydantic import ValidationError

from app.models.omm import OMMUploadForm


class TestOMMFormValidFormat:
    """Test format field validation."""
    
    def test_valid_xml_format(self):
        """Test 'xml' format is accepted."""
        form = OMMUploadForm(format='xml', source='test_source')
        assert form.format == 'xml'
    
    def test_valid_json_format(self):
        """Test 'json' format is accepted."""
        form = OMMUploadForm(format='json', source='test_source')
        assert form.format == 'json'
    
    def test_invalid_format_rejected(self):
        """Test invalid format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OMMUploadForm(format='yaml', source='test')  # type: ignore
        
        errors = exc_info.value.errors()
        assert any('format' in str(e) for e in errors)


class TestOMMFormValidSource:
    """Test source field validation and sanitization."""
    
    def test_alphanumeric_source(self):
        """Test alphanumeric source is accepted."""
        form = OMMUploadForm(format='xml', source='test123')
        assert form.source == 'test123'
    
    def test_underscore_hyphen_allowed(self):
        """Test underscore and hyphen are allowed."""
        form = OMMUploadForm(format='xml', source='test_source-2024')
        assert form.source == 'test_source-2024'
    
    def test_source_sanitized_lowercase(self):
        """Test source is converted to lowercase."""
        form = OMMUploadForm(format='xml', source='NASA_CDM_2024')
        assert form.source == 'nasa_cdm_2024'
    
    def test_source_strips_whitespace(self):
        """Test whitespace is stripped from source."""
        form = OMMUploadForm(format='xml', source='  test_source  ')
        assert form.source == 'test_source'
    
    def test_default_source(self):
        """Test default source value."""
        form = OMMUploadForm(format='xml')
        assert form.source == 'user_upload'


class TestOMMFormSecurityViolations:
    """Test that security violations are rejected."""
    
    def test_sql_injection_rejected(self):
        """Test SQL injection attempt is rejected."""
        with pytest.raises(ValidationError):
            OMMUploadForm(format='xml', source="'; DROP TABLE satellites; --")
    
    def test_xss_attempt_rejected(self):
        """Test XSS attempt is rejected."""
        with pytest.raises(ValidationError):
            OMMUploadForm(format='xml', source="<script>alert('xss')</script>")
    
    def test_path_traversal_rejected(self):
        """Test path traversal is rejected."""
        with pytest.raises(ValidationError):
            OMMUploadForm(format='xml', source="../../../etc/passwd")
    
    def test_special_chars_rejected(self):
        """Test special characters are rejected."""
        invalid_sources = [
            "test@source",
            "test$source",
            "test%source",
            "test&source",
            "test*source",
            "test source",  # space
            "test;source",
            "test|source",
        ]
        
        for source in invalid_sources:
            with pytest.raises(ValidationError):
                OMMUploadForm(format='xml', source=source)
    
    def test_max_length_enforced(self):
        """Test source max length is 100 chars."""
        long_source = "a" * 101
        
        with pytest.raises(ValidationError) as exc_info:
            OMMUploadForm(format='xml', source=long_source)
        
        errors = exc_info.value.errors()
        assert any('max_length' in str(e).lower() or 'ensure this value has at most' in str(e).lower() 
                   for e in errors)
    
    def test_empty_source_rejected(self):
        """Test empty source is rejected."""
        with pytest.raises(ValidationError):
            OMMUploadForm(format='xml', source="")
    
    def test_whitespace_only_rejected(self):
        """Test whitespace-only source is rejected."""
        with pytest.raises(ValidationError):
            OMMUploadForm(format='xml', source="   ")


class TestOMMFormEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_single_char_source(self):
        """Test single character source is accepted."""
        form = OMMUploadForm(format='xml', source='a')
        assert form.source == 'a'
    
    def test_max_valid_length(self):
        """Test maximum valid length (100 chars)."""
        max_source = "a" * 100
        form = OMMUploadForm(format='xml', source=max_source)
        assert len(form.source) == 100
    
    def test_unicode_rejected(self):
        """Test unicode characters are rejected."""
        with pytest.raises(ValidationError):
            OMMUploadForm(format='xml', source='test_源')
    
    def test_numeric_only_source(self):
        """Test numeric-only source is accepted."""
        form = OMMUploadForm(format='xml', source='123456')
        assert form.source == '123456'


@pytest.mark.integration
class TestOMMEndpointValidation:
    """Test validation is enforced at API endpoint level."""
    
    def test_invalid_source_returns_422(self, client):
        """Test invalid source in form returns 422 validation error."""
        # This requires a test client fixture
        # Placeholder for integration testing
        pass
    
    def test_valid_form_accepted(self, client):
        """Test valid form data is accepted."""
        # Placeholder for integration testing
        pass
