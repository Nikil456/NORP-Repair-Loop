"""
Configuration management for NORP Repair Loop
"""
import json
import os
from typing import Dict, Any


class Config:
    """
    Configuration class that loads settings from config.json and environment variables.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize configuration from config.json file.

        Args:
            config_path: Path to the config.json file. If None, uses default path.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")

        self._config = {}

        # Load from config.json if it exists
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
                print("Using default configuration...")

        # Override with environment variables if they exist
        self._load_env_vars()

    def _load_env_vars(self):
        """Load configuration from environment variables."""
        env_mappings = {
            'DB_URL': 'db_url',
            'DB_USERNAME': 'db_username',
            'DB_PASSWORD': 'db_password',
            'REDIS_HOST_URL': 'redis_host_url',
            'REDIS_PORT': 'redis_port',
            'REDIS_PASSWORD': 'redis_password',
            'OPENAI_API_KEY': 'openai_api_key',
            'NVIDIA_API_KEY': 'nvidia_api_key'
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self._config[config_key] = env_value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dictionary access."""
        return self._config[key]

    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self._config

    def keys(self):
        """Get all configuration keys."""
        return self._config.keys()

    def items(self):
        """Get all configuration key-value pairs."""
        return self._config.items()

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()

    def __repr__(self) -> str:
        """String representation of configuration (hiding sensitive data)."""
        safe_config = {}
        sensitive_keys = {'password', 'api_key', 'key'}

        for key, value in self._config.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_config[key] = "***HIDDEN***"
            else:
                safe_config[key] = value

        return f"Config({safe_config})"