"""
Input validation models for API endpoints.

Security: All external inputs must be validated at the boundary.
"""
from pydantic import BaseModel, Field, validator, AnyHttpUrl
from typing import Optional
import re
import ipaddress
from urllib.parse import urlparse


class NoradIdParam(BaseModel):
    """
    NORAD Catalog ID validation.
    
    NORAD IDs are 5-digit numeric identifiers (00001-99999).
    Any other format is rejected to prevent injection attacks.
    """
    value: str = Field(
        ...,
        min_length=1,
        max_length=5,
        description="NORAD catalog number (1-99999)"
    )
    
    @validator('value')
    def validate_norad_id(cls, v: str) -> str:
        """
        Validate NORAD ID format and range.
        
        Security checks:
        - Must be purely numeric (no SQL injection)
        - Length 1-5 (no path traversal like ../../)
        - Range 1-99999 (valid NORAD space)
        """
        # Strip whitespace
        v = v.strip()
        
        # Must be numeric only
        if not v.isdigit():
            raise ValueError('NORAD ID must be numeric only')
        
        # Convert to int and check range
        norad_int = int(v)
        if norad_int < 1 or norad_int > 99999:
            raise ValueError('NORAD ID must be between 1 and 99999')
        
        # Return original string (preserve leading zeros if any)
        return v
    
    def __str__(self) -> str:
        return self.value


class WebhookUrlParam(BaseModel):
    """
    Webhook URL validation with SSRF protection.
    
    Security:
    - HTTPS only (no HTTP, file://, etc.)
    - Domain allowlist
    - IP blocklist (internal networks, cloud metadata)
    - DNS resolution check
    """
    url: AnyHttpUrl
    
    # Allowed webhook domains (allowlist approach)
    ALLOWED_DOMAINS = [
        'hooks.slack.com',
        'discord.com',
        'discordapp.com',
        'hooks.zapier.com',
        'maker.ifttt.com',
        # Add more as needed
    ]
    
    # Blocked IP ranges (SSRF protection)
    BLOCKED_NETWORKS = [
        ipaddress.ip_network('10.0.0.0/8'),       # Private
        ipaddress.ip_network('172.16.0.0/12'),    # Private
        ipaddress.ip_network('192.168.0.0/16'),   # Private
        ipaddress.ip_network('127.0.0.0/8'),      # Loopback
        ipaddress.ip_network('169.254.0.0/16'),   # Link-local (AWS metadata)
        ipaddress.ip_network('224.0.0.0/4'),      # Multicast
        ipaddress.ip_network('240.0.0.0/4'),      # Reserved
        ipaddress.ip_network('::1/128'),          # IPv6 loopback
        ipaddress.ip_network('fe80::/10'),        # IPv6 link-local
    ]
    
    @validator('url')
    def validate_webhook_url(cls, v: AnyHttpUrl) -> AnyHttpUrl:
        """
        Validate webhook URL against SSRF attacks.
        
        Security checks:
        1. HTTPS only
        2. Domain must be in allowlist
        3. Resolved IP must not be in blocklist
        """
        parsed = urlparse(str(v))
        
        # Check HTTPS
        if parsed.scheme != 'https':
            raise ValueError('Only HTTPS webhooks are allowed')
        
        # Check domain allowlist
        hostname = parsed.hostname
        if not hostname:
            raise ValueError('Invalid hostname')
        
        # Check if domain or any parent domain is in allowlist
        domain_allowed = False
        for allowed_domain in cls.ALLOWED_DOMAINS:
            if hostname == allowed_domain or hostname.endswith(f'.{allowed_domain}'):
                domain_allowed = True
                break
        
        if not domain_allowed:
            raise ValueError(
                f'Domain not in allowlist: {hostname}. '
                f'Allowed domains: {", ".join(cls.ALLOWED_DOMAINS)}'
            )
        
        # Note: We don't resolve IP here to avoid blocking the request.
        # IP blocking should be done at request time with proper error handling.
        # See WebhookSecurityMiddleware for runtime IP checks.
        
        return v
    
    def __str__(self) -> str:
        return str(self.url)


class EpochParam(BaseModel):
    """
    ISO 8601 timestamp validation.
    
    Security: Prevents malformed dates that could cause parsing errors.
    """
    value: str = Field(
        ...,
        regex=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$',
        description="ISO 8601 timestamp"
    )
    
    @validator('value')
    def validate_epoch(cls, v: str) -> str:
        """Validate ISO 8601 format."""
        # Additional validation can be added here
        # For now, regex is sufficient
        return v
    
    def __str__(self) -> str:
        return self.value


class PaginationParams(BaseModel):
    """
    Pagination parameters with safe limits.
    
    Security: Prevents DoS via excessive page sizes.
    """
    limit: int = Field(
        100,
        ge=1,
        le=1000,
        description="Number of items per page (max 1000)"
    )
    offset: int = Field(
        0,
        ge=0,
        description="Number of items to skip"
    )


class SatelliteIdList(BaseModel):
    """
    List of NORAD IDs with size limit.
    
    Security: Prevents DoS via massive lists.
    """
    satellite_ids: list[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of NORAD catalog numbers (max 100)"
    )
    
    @validator('satellite_ids', each_item=True)
    def validate_each_id(cls, v: str) -> str:
        """Validate each NORAD ID in the list."""
        # Reuse NoradIdParam validation
        validated = NoradIdParam(value=v)
        return validated.value
