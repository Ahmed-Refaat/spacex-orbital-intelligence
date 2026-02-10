"""
Logging sanitizer to prevent secret leakage.

Security: Ensures no sensitive data leaks into logs.
"""
import re
from typing import Any, Dict


# Patterns to detect secrets
SECRET_PATTERNS = [
    # API keys (specific patterns first for better matching)
    (r'J5ACSV-H8HVFU-BN3F86-5NMK', '[REDACTED_N2YO_KEY]'),  # N2YO specific pattern
    (r'[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{4}', '[REDACTED_N2YO_KEY]'),  # N2YO format
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})', '[REDACTED_API_KEY]'),
    (r'apikey["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})', '[REDACTED_API_KEY]'),
    
    # Tokens
    (r'token["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{20,})', '[REDACTED_TOKEN]'),
    (r'bearer\s+([A-Za-z0-9_\-\.]{20,})', '[REDACTED_BEARER_TOKEN]'),
    
    # Passwords
    (r'password["\']?\s*[:=]\s*["\']?([^\s"\']{8,})', '[REDACTED_PASSWORD]'),
    (r'passwd["\']?\s*[:=]\s*["\']?([^\s"\']{8,})', '[REDACTED_PASSWORD]'),
    (r'pwd["\']?\s*[:=]\s*["\']?([^\s"\']{8,})', '[REDACTED_PASSWORD]'),
    
    # AWS keys
    (r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]'),
    (r'aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})', '[REDACTED_AWS_SECRET]'),
    
    # Private keys
    (r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----', '[REDACTED_PRIVATE_KEY]'),
    
    # Database connection strings
    (r'(postgres|mysql|mongodb)://[^:\s]+:([^@\s]+)@', r'\1://[REDACTED_USER]:[REDACTED_PASSWORD]@'),
    
    # Email addresses (optional - depends on policy)
    # (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]'),
    
    # IP addresses in some contexts (optional)
    # (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[REDACTED_IP]'),
]


def sanitize_string(text: str) -> str:
    """
    Sanitize a string by redacting secrets.
    
    Args:
        text: Input string that may contain secrets
        
    Returns:
        Sanitized string with secrets redacted
    """
    if not text:
        return text
    
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary.
    
    Args:
        data: Dictionary that may contain secrets
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    
    # Keys that should always be redacted
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
        'private_key', 'access_key', 'secret_key', 'authorization', 'auth',
        'cookie', 'session', 'csrf_token', 'jwt'
    }
    
    for key, value in data.items():
        # Check if key is sensitive
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            sanitized[key] = '[REDACTED]'
        # Recursively sanitize nested dicts
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        # Recursively sanitize lists
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item) if isinstance(item, dict)
                else sanitize_string(str(item)) if isinstance(item, str)
                else item
                for item in value
            ]
        # Sanitize strings
        elif isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_log_record(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a structlog record before emission.
    
    This is the processor that should be added to structlog pipeline.
    
    Args:
        logger: Logger instance (unused, required by structlog)
        method_name: Log method name (unused, required by structlog)
        event_dict: Log record from structlog
        
    Returns:
        Sanitized log record
    """
    # Sanitize all values in the event dict
    return sanitize_dict(event_dict)


# Example usage in structlog configuration
def configure_secure_logging():
    """
    Configure structlog with security sanitization.
    
    Add this to your structlog.configure() call:
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            sanitize_log_record,  # ← Add sanitizer here
            structlog.processors.JSONRenderer()
        ],
        ...
    )
    """
    import structlog
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            sanitize_log_record,  # Security: Redact secrets
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
