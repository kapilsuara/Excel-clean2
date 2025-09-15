"""
Configuration module for Excel Data Cleaner
Handles both Streamlit secrets and environment variables
"""

import os
import streamlit as st
from typing import Optional

def get_config_value(key: str, section: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """
    Get configuration value from environment variables or Streamlit secrets.
    
    Priority:
    1. Environment variables (for local development with .env)
    2. Streamlit secrets (for deployment)
    3. Default value
    
    Args:
        key: The configuration key
        section: Optional section in secrets.toml
        default: Default value if not found
    
    Returns:
        Configuration value or default
    """
    # Try environment variables first (prioritize .env file)
    env_key = f"{section}_{key}" if section else key
    env_value = os.getenv(env_key.upper())
    if env_value:
        return env_value
    
    # Fall back to Streamlit secrets
    try:
        if section:
            # Access nested configuration
            if section in st.secrets:
                if key in st.secrets[section]:
                    return st.secrets[section][key]
        else:
            # Access top-level configuration
            if key in st.secrets:
                return st.secrets[key]
    except Exception:
        # Streamlit secrets not available (local development)
        pass
    
    # Return default
    return default

# API Keys
def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key from environment or secrets."""
    # First try direct environment variable (from .env)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return api_key
    # Fall back to config value (which also checks env and secrets)
    return get_config_value("ANTHROPIC_API_KEY")

def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from secrets or environment."""
    return get_config_value("OPENAI_API_KEY", section="openai")

# AWS Configuration
def get_aws_config() -> dict:
    """Get AWS configuration from secrets or environment."""
    return {
        "aws_access_key_id": get_config_value("AWS_ACCESS_KEY_ID") or get_config_value("AWS_ACCESS_KEY_ID", section="aws"),
        "aws_secret_access_key": get_config_value("AWS_SECRET_ACCESS_KEY") or get_config_value("AWS_SECRET_ACCESS_KEY", section="aws"),
        "region_name": get_config_value("AWS_REGION") or get_config_value("AWS_DEFAULT_REGION", section="aws", default="us-east-1"),
        "bucket_name": get_config_value("S3_BUCKET_NAME") or get_config_value("S3_BUCKET_NAME", section="aws", default="excel-cleaner-storage")
    }

# Application Settings
def get_app_settings() -> dict:
    """Get application settings from secrets or environment."""
    def parse_bool(value: Optional[str], default: bool = True) -> bool:
        """Parse a string value to boolean, handling None."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() == "true"
    
    return {
        "max_file_size_mb": int(get_config_value("MAX_FILE_SIZE_MB", section="app", default="100")),
        "enable_logging": parse_bool(get_config_value("ENABLE_LOGGING", section="app", default="true")),
        "log_level": get_config_value("LOG_LEVEL", section="app", default="INFO"),
        "session_timeout_minutes": int(get_config_value("SESSION_TIMEOUT_MINUTES", section="app", default="60"))
    }

# Feature Flags
def get_feature_flags() -> dict:
    """Get feature flags from secrets or environment."""
    def parse_bool(value: Optional[str], default: bool = True) -> bool:
        """Parse a string value to boolean, handling None."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() == "true"
    
    return {
        "enable_ai_header_detection": parse_bool(get_config_value("ENABLE_AI_HEADER_DETECTION", section="features", default="true")),
        "enable_format_standardization": parse_bool(get_config_value("ENABLE_FORMAT_STANDARDIZATION", section="features", default="true")),
        "enable_multi_sheet_support": parse_bool(get_config_value("ENABLE_MULTI_SHEET_SUPPORT", section="features", default="true")),
        "enable_s3_storage": parse_bool(get_config_value("ENABLE_S3_STORAGE", section="features", default="true")),
        "enable_agent_assessment": parse_bool(get_config_value("ENABLE_AGENT_ASSESSMENT", section="features", default="true"))
    }

# Rate Limits
def get_rate_limits() -> dict:
    """Get rate limiting configuration from secrets or environment."""
    return {
        "max_requests_per_minute": int(get_config_value("MAX_REQUESTS_PER_MINUTE", section="rate_limits", default="60")),
        "max_ai_calls_per_minute": int(get_config_value("MAX_AI_CALLS_PER_MINUTE", section="rate_limits", default="20")),
        "max_file_uploads_per_hour": int(get_config_value("MAX_FILE_UPLOADS_PER_HOUR", section="rate_limits", default="100"))
    }

# Validation
def validate_config() -> tuple[bool, list[str]]:
    """
    Validate that required configuration is present.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required credentials
    if not get_anthropic_api_key():
        errors.append("Missing ANTHROPIC_API_KEY")
    
    aws_config = get_aws_config()
    if get_feature_flags()["enable_s3_storage"]:
        if not aws_config["aws_access_key_id"]:
            errors.append("Missing AWS_ACCESS_KEY_ID")
        if not aws_config["aws_secret_access_key"]:
            errors.append("Missing AWS_SECRET_ACCESS_KEY")
        if not aws_config["bucket_name"]:
            errors.append("Missing S3_BUCKET_NAME")
    
    return len(errors) == 0, errors