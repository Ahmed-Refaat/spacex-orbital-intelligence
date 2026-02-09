"""
Secrets Management - Production-Grade

For production deployments, use:
- AWS Secrets Manager
- HashiCorp Vault
- Google Secret Manager
- Azure Key Vault

DO NOT use .env files in production!
"""
import os
from typing import Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class SecretsManager:
    """
    Abstract secrets manager with multiple backend support.
    
    In development: Falls back to .env
    In production: Use cloud secrets manager
    """
    
    def __init__(self, backend: str = "env"):
        """
        Initialize secrets manager.
        
        Args:
            backend: "env" (dev), "aws" (prod), "vault" (prod)
        """
        self.backend = backend
        self._cache: Dict[str, str] = {}
        
        if backend not in ["env", "aws", "vault", "gcp"]:
            raise ValueError(f"Unsupported backend: {backend}")
        
        logger.info("secrets_manager_initialized", backend=backend)
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret value by key.
        
        Args:
            key: Secret key (e.g., "spacetrack_password")
            default: Default value if not found
        
        Returns:
            Secret value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Dispatch to backend
        if self.backend == "env":
            value = self._get_from_env(key, default)
        elif self.backend == "aws":
            value = self._get_from_aws(key, default)
        elif self.backend == "vault":
            value = self._get_from_vault(key, default)
        elif self.backend == "gcp":
            value = self._get_from_gcp(key, default)
        else:
            value = default
        
        # Cache for this request
        if value:
            self._cache[key] = value
        
        return value
    
    def _get_from_env(self, key: str, default: Optional[str]) -> Optional[str]:
        """Get from environment variable (development only)."""
        return os.getenv(key.upper(), default)
    
    def _get_from_aws(self, key: str, default: Optional[str]) -> Optional[str]:
        """
        Get from AWS Secrets Manager.
        
        Example:
            >>> manager = SecretsManager("aws")
            >>> password = manager.get_secret("spacetrack_password")
        """
        try:
            import boto3
            import json
            
            client = boto3.client('secretsmanager')
            
            # Get secret bundle (contains multiple secrets)
            secret_name = os.getenv("AWS_SECRET_NAME", "spacex-orbital/prod")
            response = client.get_secret_value(SecretId=secret_name)
            
            # Parse JSON
            secrets = json.loads(response['SecretString'])
            
            return secrets.get(key, default)
            
        except ImportError:
            logger.error("boto3 not installed", action="pip install boto3")
            return default
        except Exception as e:
            logger.error("aws_secrets_error", key=key, error=str(e))
            return default
    
    def _get_from_vault(self, key: str, default: Optional[str]) -> Optional[str]:
        """
        Get from HashiCorp Vault.
        
        Example:
            >>> manager = SecretsManager("vault")
            >>> password = manager.get_secret("spacetrack_password")
        """
        try:
            import hvac
            
            vault_url = os.getenv("VAULT_ADDR", "http://localhost:8200")
            vault_token = os.getenv("VAULT_TOKEN")
            
            client = hvac.Client(url=vault_url, token=vault_token)
            
            # Read from KV v2
            secret_path = os.getenv("VAULT_SECRET_PATH", "spacex-orbital/prod")
            response = client.secrets.kv.v2.read_secret_version(path=secret_path)
            
            secrets = response['data']['data']
            return secrets.get(key, default)
            
        except ImportError:
            logger.error("hvac not installed", action="pip install hvac")
            return default
        except Exception as e:
            logger.error("vault_secrets_error", key=key, error=str(e))
            return default
    
    def _get_from_gcp(self, key: str, default: Optional[str]) -> Optional[str]:
        """
        Get from Google Secret Manager.
        
        Example:
            >>> manager = SecretsManager("gcp")
            >>> password = manager.get_secret("spacetrack_password")
        """
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            project_id = os.getenv("GCP_PROJECT_ID")
            secret_name = f"projects/{project_id}/secrets/{key}/versions/latest"
            
            response = client.access_secret_version(request={"name": secret_name})
            return response.payload.data.decode('utf-8')
            
        except ImportError:
            logger.error("google-cloud-secret-manager not installed")
            return default
        except Exception as e:
            logger.error("gcp_secrets_error", key=key, error=str(e))
            return default


# Global instance
# For production: Change to "aws", "vault", or "gcp"
secrets_manager = SecretsManager(backend=os.getenv("SECRETS_BACKEND", "env"))


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get secrets.
    
    Usage:
        >>> from app.core.secrets import get_secret
        >>> password = get_secret("spacetrack_password")
    """
    return secrets_manager.get_secret(key, default)
