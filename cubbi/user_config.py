"""
User configuration manager for Cubbi Container Tool.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Define the environment variable mappings for auto-discovery
STANDARD_PROVIDERS = {
    "anthropic": {
        "type": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "type": "openai",
        "env_key": "OPENAI_API_KEY",
    },
    "google": {
        "type": "google",
        "env_key": "GOOGLE_API_KEY",
    },
    "openrouter": {
        "type": "openrouter",
        "env_key": "OPENROUTER_API_KEY",
    },
}

# Legacy environment variable mappings (kept for backward compatibility)
LEGACY_ENV_MAPPINGS = {
    "services.langfuse.url": "LANGFUSE_URL",
    "services.langfuse.public_key": "LANGFUSE_INIT_PROJECT_PUBLIC_KEY",
    "services.langfuse.secret_key": "LANGFUSE_INIT_PROJECT_SECRET_KEY",
    "services.openai.api_key": "OPENAI_API_KEY",
    "services.openai.url": "OPENAI_URL",
    "services.anthropic.api_key": "ANTHROPIC_API_KEY",
    "services.openrouter.api_key": "OPENROUTER_API_KEY",
    "services.google.api_key": "GOOGLE_API_KEY",
}


class UserConfigManager:
    """Manager for user-specific configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the user configuration manager.

        Args:
            config_path: Optional path to the configuration file.
                         Defaults to ~/.config/cubbi/config.yaml.
        """
        # Default to ~/.config/cubbi/config.yaml
        self.config_path = Path(
            config_path or os.path.expanduser("~/.config/cubbi/config.yaml")
        )
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create with defaults if it doesn't exist."""
        if not self.config_path.exists():
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Create default config
            default_config = self._get_default_config()

            # Auto-discover and add providers from environment for new configs
            self._auto_discover_providers(default_config)

            # Save to file
            with open(self.config_path, "w") as f:
                yaml.safe_dump(default_config, f)
            # Set secure permissions
            os.chmod(self.config_path, 0o600)
            return default_config

        # Load existing config with error handling
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f) or {}

            # Check for backup file that might be newer
            backup_path = self.config_path.with_suffix(".yaml.bak")
            if backup_path.exists():
                # Check if backup is newer than main config
                if backup_path.stat().st_mtime > self.config_path.stat().st_mtime:
                    try:
                        with open(backup_path, "r") as f:
                            backup_config = yaml.safe_load(f) or {}
                        print("Found newer backup config, using that instead")
                        config = backup_config
                    except Exception as e:
                        print(f"Failed to load backup config: {e}")

        except Exception as e:
            print(f"Error loading configuration: {e}")
            # Try to load from backup if main config is corrupted
            backup_path = self.config_path.with_suffix(".yaml.bak")
            if backup_path.exists():
                try:
                    with open(backup_path, "r") as f:
                        config = yaml.safe_load(f) or {}
                    print("Loaded configuration from backup file")
                except Exception as backup_e:
                    print(f"Failed to load backup configuration: {backup_e}")
                    config = {}
            else:
                config = {}

        # Merge with defaults for any missing fields
        config = self._merge_with_defaults(config)

        # Auto-discover and add providers from environment
        self._auto_discover_providers(config)

        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration."""
        return {
            "defaults": {
                "image": "goose",
                "connect": True,
                "mount_local": True,
                "networks": [],  # Default networks to connect to (besides cubbi-network)
                "volumes": [],  # Default volumes to mount, format: "source:dest"
                "ports": [],  # Default ports to forward, format: list of integers
                "mcps": [],  # Default MCP servers to connect to
                "model": "anthropic/claude-3-5-sonnet-latest",  # Default LLM model (provider/model format)
            },
            "providers": {},  # LLM providers configuration
            "services": {
                "langfuse": {},  # Keep langfuse in services as it's not an LLM provider
            },
            "docker": {
                "network": "cubbi-network",
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
            key_path: The configuration path (e.g., "defaults.image")
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
                for section in ["defaults", "docker", "remote", "ui", "providers"]
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
            key_path: The configuration path (e.g., "defaults.image")
            value: The value to set
        """
        # Handle shorthand service paths (e.g., "langfuse.url")
        if (
            "." in key_path
            and not key_path.startswith("services.")
            and not any(
                key_path.startswith(section + ".")
                for section in ["defaults", "docker", "remote", "ui", "providers"]
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
        """Save the configuration to file with error handling and backup."""
        # Create backup of existing config file if it exists
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix(".yaml.bak")
            try:
                import shutil

                shutil.copy2(self.config_path, backup_path)
            except Exception as e:
                print(f"Warning: Failed to create config backup: {e}")

        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Write to a temporary file first
            temp_path = self.config_path.with_suffix(".yaml.tmp")
            with open(temp_path, "w") as f:
                yaml.safe_dump(self.config, f)

            # Set secure permissions on temp file
            os.chmod(temp_path, 0o600)

            # Rename temp file to actual config file (atomic operation)
            # Use os.replace which is atomic on Unix systems
            os.replace(temp_path, self.config_path)

        except Exception as e:
            print(f"Error saving configuration: {e}")
            # If we have a backup and the save failed, try to restore from backup
            backup_path = self.config_path.with_suffix(".yaml.bak")
            if backup_path.exists():
                try:
                    import shutil

                    shutil.copy2(backup_path, self.config_path)
                    print("Restored configuration from backup")
                except Exception as restore_error:
                    print(
                        f"Failed to restore configuration from backup: {restore_error}"
                    )

    def reset(self) -> None:
        """Reset the configuration to defaults."""
        self.config = self._get_default_config()
        self.save()

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables from the configuration.

        NOTE: API keys are now handled by cubbi_init plugins, not passed from host.

        Returns:
            A dictionary of environment variables to set in the container.
        """
        env_vars = {}

        # Process the legacy service configurations and map to environment variables
        # BUT EXCLUDE API KEYS - they're now handled by cubbi_init
        for config_path, env_var in LEGACY_ENV_MAPPINGS.items():
            # Skip API key environment variables - let cubbi_init handle them
            if any(
                key_word in env_var.upper() for key_word in ["API_KEY", "SECRET_KEY"]
            ):
                continue

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

        # NOTE: Provider API keys are no longer passed as environment variables
        # They are now handled by cubbi_init plugins based on selected model
        # This prevents unused API keys from being exposed in containers

        return env_vars

    def get_provider_environment_variables(self, provider_name: str) -> Dict[str, str]:
        """Get environment variables for a specific provider.

        Args:
            provider_name: Name of the provider to get environment variables for

        Returns:
            Dictionary of environment variables for the provider
        """
        env_vars = {}
        provider_config = self.get_provider(provider_name)

        if not provider_config:
            return env_vars

        provider_type = provider_config.get("type", provider_name)
        api_key = provider_config.get("api_key", "")
        base_url = provider_config.get("base_url")

        # Resolve environment variable references
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var_name = api_key[2:-1]
            resolved_api_key = os.environ.get(env_var_name, "")
        else:
            resolved_api_key = api_key

        if not resolved_api_key:
            return env_vars

        # Add environment variables based on provider type
        if provider_type == "anthropic":
            env_vars["ANTHROPIC_API_KEY"] = resolved_api_key
        elif provider_type == "openai":
            env_vars["OPENAI_API_KEY"] = resolved_api_key
            if base_url:
                env_vars["OPENAI_URL"] = base_url
        elif provider_type == "google":
            env_vars["GOOGLE_API_KEY"] = resolved_api_key
        elif provider_type == "openrouter":
            env_vars["OPENROUTER_API_KEY"] = resolved_api_key

        return env_vars

    def get_all_providers_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for all configured providers.

        Returns:
            Dictionary of all provider environment variables
        """
        env_vars = {}
        providers = self.get("providers", {})

        for provider_name in providers.keys():
            provider_env = self.get_provider_environment_variables(provider_name)
            env_vars.update(provider_env)

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

    def _auto_discover_providers(self, config: Dict[str, Any]) -> None:
        """Auto-discover providers from environment variables."""
        if "providers" not in config:
            config["providers"] = {}

        for provider_name, provider_info in STANDARD_PROVIDERS.items():
            # Skip if provider already configured
            if provider_name in config["providers"]:
                continue

            # Check if environment variable exists
            api_key = os.environ.get(provider_info["env_key"])
            if api_key:
                config["providers"][provider_name] = {
                    "type": provider_info["type"],
                    "api_key": f"${{{provider_info['env_key']}}}",  # Reference to env var
                }

    def get_provider(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get a provider configuration by name."""
        return self.get(f"providers.{provider_name}")

    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured providers."""
        return self.get("providers", {})

    def add_provider(
        self,
        name: str,
        provider_type: str,
        api_key: str,
        base_url: Optional[str] = None,
        env_key: Optional[str] = None,
    ) -> None:
        """Add a new provider configuration.

        Args:
            name: Provider name/identifier
            provider_type: Type of provider (anthropic, openai, etc.)
            api_key: API key value or environment variable reference
            base_url: Custom base URL for API calls (optional)
            env_key: If provided, use env reference instead of direct api_key
        """
        provider_config = {
            "type": provider_type,
            "api_key": f"${{{env_key}}}" if env_key else api_key,
        }

        if base_url:
            provider_config["base_url"] = base_url

        self.set(f"providers.{name}", provider_config)

    def remove_provider(self, name: str) -> bool:
        """Remove a provider configuration.

        Returns:
            True if provider was removed, False if it didn't exist
        """
        providers = self.get("providers", {})
        if name in providers:
            del providers[name]
            self.set("providers", providers)
            return True
        return False

    def resolve_model(self, model_spec: str) -> Optional[Dict[str, Any]]:
        """Resolve a model specification (provider/model) to provider config.

        Args:
            model_spec: Model specification in format "provider/model"

        Returns:
            Dictionary with resolved provider config and model name
        """
        if "/" not in model_spec:
            # Legacy format - try to use as provider name with empty model
            provider_name = model_spec
            model_name = ""
        else:
            provider_name, model_name = model_spec.split("/", 1)

        provider_config = self.get_provider(provider_name)
        if not provider_config:
            return None

        # Resolve environment variable references in API key
        api_key = provider_config.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var_name = api_key[2:-1]
            resolved_api_key = os.environ.get(env_var_name, "")
        else:
            resolved_api_key = api_key

        return {
            "provider_name": provider_name,
            "provider_type": provider_config.get("type", provider_name),
            "model_name": model_name,
            "api_key": resolved_api_key,
            "base_url": provider_config.get("base_url"),
        }

    # Resource management methods
    def list_mcps(self) -> List[str]:
        """Get all configured default MCP servers."""
        return self.get("defaults.mcps", [])

    def add_mcp(self, name: str) -> None:
        """Add a new default MCP server."""
        mcps = self.list_mcps()
        if name not in mcps:
            mcps.append(name)
            self.set("defaults.mcps", mcps)

    def remove_mcp(self, name: str) -> bool:
        """Remove a default MCP server.

        Returns:
            True if MCP was removed, False if it didn't exist
        """
        mcps = self.list_mcps()
        if name in mcps:
            mcps.remove(name)
            self.set("defaults.mcps", mcps)
            return True
        return False

    def list_mcp_configurations(self) -> List[Dict[str, Any]]:
        """Get all configured MCP server configurations."""
        return self.get("mcps", [])

    def get_mcp_configuration(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an MCP configuration by name."""
        mcps = self.list_mcp_configurations()
        for mcp in mcps:
            if mcp.get("name") == name:
                return mcp
        return None

    def add_mcp_configuration(self, mcp_config: Dict[str, Any]) -> None:
        """Add a new MCP server configuration."""
        mcps = self.list_mcp_configurations()

        # Remove existing MCP with the same name if it exists
        mcps = [mcp for mcp in mcps if mcp.get("name") != mcp_config.get("name")]

        # Add the new MCP
        mcps.append(mcp_config)

        # Save the configuration
        self.set("mcps", mcps)

    def remove_mcp_configuration(self, name: str) -> bool:
        """Remove an MCP server configuration.

        Returns:
            True if MCP was removed, False if it didn't exist
        """
        mcps = self.list_mcp_configurations()
        original_length = len(mcps)

        # Filter out the MCP with the specified name
        mcps = [mcp for mcp in mcps if mcp.get("name") != name]

        if len(mcps) < original_length:
            self.set("mcps", mcps)

            # Also remove from defaults if it's there
            self.remove_mcp(name)
            return True
        return False

    def list_networks(self) -> List[str]:
        """Get all configured default networks."""
        return self.get("defaults.networks", [])

    def add_network(self, name: str) -> None:
        """Add a new default network."""
        networks = self.list_networks()
        if name not in networks:
            networks.append(name)
            self.set("defaults.networks", networks)

    def remove_network(self, name: str) -> bool:
        """Remove a default network.

        Returns:
            True if network was removed, False if it didn't exist
        """
        networks = self.list_networks()
        if name in networks:
            networks.remove(name)
            self.set("defaults.networks", networks)
            return True
        return False

    def list_volumes(self) -> List[str]:
        """Get all configured default volumes."""
        return self.get("defaults.volumes", [])

    def add_volume(self, volume: str) -> None:
        """Add a new default volume mapping."""
        volumes = self.list_volumes()
        if volume not in volumes:
            volumes.append(volume)
            self.set("defaults.volumes", volumes)

    def remove_volume(self, volume: str) -> bool:
        """Remove a default volume mapping.

        Returns:
            True if volume was removed, False if it didn't exist
        """
        volumes = self.list_volumes()
        if volume in volumes:
            volumes.remove(volume)
            self.set("defaults.volumes", volumes)
            return True
        return False

    def list_ports(self) -> List[int]:
        """Get all configured default ports."""
        return self.get("defaults.ports", [])

    def add_port(self, port: int) -> None:
        """Add a new default port."""
        ports = self.list_ports()
        if port not in ports:
            ports.append(port)
            self.set("defaults.ports", ports)

    def remove_port(self, port: int) -> bool:
        """Remove a default port.

        Returns:
            True if port was removed, False if it didn't exist
        """
        ports = self.list_ports()
        if port in ports:
            ports.remove(port)
            self.set("defaults.ports", ports)
            return True
        return False

    # Model management methods
    def list_provider_models(self, provider_name: str) -> List[Dict[str, str]]:
        """Get all models for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of model dictionaries with 'id' and 'name' keys
        """
        provider_config = self.get_provider(provider_name)
        if not provider_config:
            return []

        models = provider_config.get("models", [])
        normalized_models = []
        for model in models:
            if isinstance(model, str):
                normalized_models.append({"id": model})
            elif isinstance(model, dict):
                model_id = model.get("id", "")
                if model_id:
                    normalized_models.append({"id": model_id})

        return normalized_models

    def set_provider_models(
        self, provider_name: str, models: List[Dict[str, str]]
    ) -> None:
        """Set the models for a specific provider.

        Args:
            provider_name: Name of the provider
            models: List of model dictionaries with 'id' and optional 'name' keys
        """
        provider_config = self.get_provider(provider_name)
        if not provider_config:
            return

        # Normalize models - ensure each has id, name defaults to id
        normalized_models = []
        for model in models:
            if isinstance(model, dict) and "id" in model:
                normalized_model = {
                    "id": model["id"],
                }
                normalized_models.append(normalized_model)

        provider_config["models"] = normalized_models
        self.set(f"providers.{provider_name}", provider_config)

    def add_provider_model(
        self, provider_name: str, model_id: str, model_name: Optional[str] = None
    ) -> None:
        """Add a model to a provider.

        Args:
            provider_name: Name of the provider
            model_id: ID of the model
            model_name: Optional display name for the model (defaults to model_id)
        """
        models = self.list_provider_models(provider_name)

        for existing_model in models:
            if existing_model["id"] == model_id:
                return

        new_model = {"id": model_id}
        models.append(new_model)
        self.set_provider_models(provider_name, models)

    def remove_provider_model(self, provider_name: str, model_id: str) -> bool:
        """Remove a model from a provider.

        Args:
            provider_name: Name of the provider
            model_id: ID of the model to remove

        Returns:
            True if model was removed, False if it didn't exist
        """
        models = self.list_provider_models(provider_name)
        original_length = len(models)

        # Filter out the model with the specified ID
        models = [model for model in models if model["id"] != model_id]

        if len(models) < original_length:
            self.set_provider_models(provider_name, models)
            return True
        return False

    def is_provider_openai_compatible(self, provider_name: str) -> bool:
        provider_config = self.get_provider(provider_name)
        if not provider_config:
            return False

        provider_type = provider_config.get("type", "")
        return provider_type == "openai" and provider_config.get("base_url") is not None

    def supports_model_fetching(self, provider_name: str) -> bool:
        """Check if a provider supports model fetching via API."""
        from .config import PROVIDER_DEFAULT_URLS

        provider = self.get_provider(provider_name)
        if not provider:
            return False

        provider_type = provider.get("type")
        base_url = provider.get("base_url")

        # Provider supports model fetching if:
        # 1. It has a custom base_url (OpenAI-compatible), OR
        # 2. It's a standard provider type that we support
        return base_url is not None or provider_type in PROVIDER_DEFAULT_URLS

    def list_openai_compatible_providers(self) -> List[str]:
        providers = self.list_providers()
        compatible_providers = []

        for provider_name in providers.keys():
            if self.is_provider_openai_compatible(provider_name):
                compatible_providers.append(provider_name)

        return compatible_providers

    def list_model_fetchable_providers(self) -> List[str]:
        """List all providers that support model fetching."""
        providers = self.list_providers()
        fetchable_providers = []

        for provider_name in providers.keys():
            if self.supports_model_fetching(provider_name):
                fetchable_providers.append(provider_name)

        return fetchable_providers
