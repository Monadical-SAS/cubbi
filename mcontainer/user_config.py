"""
User configuration manager for Monadical Container Tool.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

# Define the environment variable mappings
ENV_MAPPINGS = {
    "services.langfuse.url": "LANGFUSE_URL",
    "services.langfuse.public_key": "LANGFUSE_INIT_PROJECT_PUBLIC_KEY",
    "services.langfuse.secret_key": "LANGFUSE_INIT_PROJECT_SECRET_KEY",
    "services.openai.api_key": "OPENAI_API_KEY",
    "services.anthropic.api_key": "ANTHROPIC_API_KEY",
    "services.openrouter.api_key": "OPENROUTER_API_KEY",
}


class UserConfigManager:
    """Manager for user-specific configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the user configuration manager.

        Args:
            config_path: Optional path to the configuration file.
                         Defaults to ~/.config/mc/config.yaml.
        """
        # Default to ~/.config/mc/config.yaml
        self.config_path = Path(
            config_path or os.path.expanduser("~/.config/mc/config.yaml")
        )
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create with defaults if it doesn't exist."""
        if not self.config_path.exists():
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Create default config
            default_config = self._get_default_config()
            # Save to file
            with open(self.config_path, "w") as f:
                yaml.safe_dump(default_config, f)
            # Set secure permissions
            os.chmod(self.config_path, 0o600)
            return default_config

        # Load existing config
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f) or {}

        # Merge with defaults for any missing fields
        return self._merge_with_defaults(config)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration."""
        return {
            "defaults": {
                "driver": "goose",
                "connect": True,
                "mount_local": True,
                "networks": [],  # Default networks to connect to (besides mc-network)
            },
            "services": {
                "langfuse": {},
                "openai": {},
                "anthropic": {},
                "openrouter": {},
            },
            "docker": {
                "network": "mc-network",
            },
            "ui": {
                "colors": True,
                "verbose": False,
            },
        }

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with defaults for missing values."""
        defaults = self._get_default_config()

        # Deep merge of config with defaults
        def _deep_merge(source, destination):
            for key, value in source.items():
                if key not in destination:
                    destination[key] = value
                elif isinstance(value, dict) and isinstance(destination[key], dict):
                    _deep_merge(value, destination[key])
            return destination

        return _deep_merge(defaults, config)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation path.

        Args:
            key_path: The configuration path (e.g., "defaults.driver")
            default: The default value to return if not found

        Returns:
            The configuration value or default if not found
        """
        # Handle shorthand service paths (e.g., "langfuse.url")
        if (
            "." in key_path
            and not key_path.startswith("services.")
            and not any(
                key_path.startswith(section + ".")
                for section in ["defaults", "docker", "remote", "ui"]
            )
        ):
            service, setting = key_path.split(".", 1)
            key_path = f"services.{service}.{setting}"

        parts = key_path.split(".")
        result = self.config

        for part in parts:
            if part not in result:
                return default
            result = result[part]

        return result

    def set(self, key_path: str, value: Any) -> None:
        """Set a configuration value by dot-notation path.

        Args:
            key_path: The configuration path (e.g., "defaults.driver")
            value: The value to set
        """
        # Handle shorthand service paths (e.g., "langfuse.url")
        if (
            "." in key_path
            and not key_path.startswith("services.")
            and not any(
                key_path.startswith(section + ".")
                for section in ["defaults", "docker", "remote", "ui"]
            )
        ):
            service, setting = key_path.split(".", 1)
            key_path = f"services.{service}.{setting}"

        parts = key_path.split(".")
        config = self.config

        # Navigate to the containing dictionary
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]

        # Set the value
        config[parts[-1]] = value
        self.save()

    def save(self) -> None:
        """Save the configuration to file."""
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.config, f)

    def reset(self) -> None:
        """Reset the configuration to defaults."""
        self.config = self._get_default_config()
        self.save()

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables from the configuration.

        Returns:
            A dictionary of environment variables to set in the container.
        """
        env_vars = {}

        # Process the service configurations and map to environment variables
        for config_path, env_var in ENV_MAPPINGS.items():
            value = self.get(config_path)
            if value:
                # Handle environment variable references
                if (
                    isinstance(value, str)
                    and value.startswith("${")
                    and value.endswith("}")
                ):
                    env_var_name = value[2:-1]
                    value = os.environ.get(env_var_name, "")

                env_vars[env_var] = str(value)

        return env_vars

    def list_config(self) -> List[Tuple[str, Any]]:
        """List all configuration values as flattened key-value pairs.

        Returns:
            A list of (key, value) tuples with flattened key paths.
        """
        result = []

        def _flatten_dict(d, prefix=""):
            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    _flatten_dict(value, full_key)
                else:
                    # Mask sensitive values
                    if any(
                        substr in full_key.lower()
                        for substr in ["key", "token", "secret", "password"]
                    ):
                        displayed_value = "*****" if value else value
                    else:
                        displayed_value = value
                    result.append((full_key, displayed_value))

        _flatten_dict(self.config)
        return sorted(result)
