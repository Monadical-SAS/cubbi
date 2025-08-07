#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Any, Dict

from cubbi_init import ToolPlugin, cubbi_config

# Standard providers that Crush supports natively
STANDARD_PROVIDERS = ["anthropic", "openai", "google", "openrouter"]


class CrushPlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "crush"

    def _get_user_ids(self) -> tuple[int, int]:
        return cubbi_config.user.uid, cubbi_config.user.gid

    def _set_ownership(self, path: Path) -> None:
        user_id, group_id = self._get_user_ids()
        try:
            os.chown(path, user_id, group_id)
        except OSError as e:
            self.status.log(f"Failed to set ownership for {path}: {e}", "WARNING")

    def _get_user_config_path(self) -> Path:
        return Path("/home/cubbi/.config/crush")

    def _map_provider_to_crush_format(
        self, provider_name: str, provider_config, is_default_provider: bool = False
    ) -> Dict[str, Any] | None:
        """Map cubbi provider configuration to crush provider format"""

        if not provider_config.base_url:
            if provider_config.type in STANDARD_PROVIDERS:
                provider_entry = {
                    "api_key": provider_config.api_key,
                }
                return provider_entry

        # Custom provider - include base_url and name
        provider_entry = {
            "api_key": provider_config.api_key,
            "base_url": provider_config.base_url,
            "models": [],
        }

        # Add name and type for custom providers
        if provider_config.type in STANDARD_PROVIDERS:
            # Standard provider with custom URL - determine type and name
            if provider_config.type == "anthropic":
                provider_entry["type"] = "anthropic"
            elif provider_config.type == "openai":
                provider_entry["type"] = "openai"
            elif provider_config.type == "google":
                provider_entry["type"] = "gemini"
            elif provider_config.type == "openrouter":
                provider_entry["type"] = "openai"
            # Set name format as 'provider_name (type)'
            provider_entry["name"] = f"{provider_name} ({provider_config.type})"
        else:
            # Non-standard provider with custom URL
            provider_entry["type"] = "openai"
            provider_entry["name"] = f"{provider_name} ({provider_config.type})"

        return provider_entry

    def _ensure_user_config_dir(self) -> Path:
        config_dir = self._get_user_config_path()

        # Create the full directory path
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            # Directory already exists, which is fine
            pass
        except OSError as e:
            self.status.log(
                f"Failed to create config directory {config_dir}: {e}", "ERROR"
            )
            return config_dir

        # Set ownership for the directories
        config_parent = config_dir.parent
        if config_parent.exists():
            self._set_ownership(config_parent)

        if config_dir.exists():
            self._set_ownership(config_dir)

        return config_dir

    def initialize(self) -> bool:
        self._ensure_user_config_dir()
        return self.setup_tool_configuration()

    def setup_tool_configuration(self) -> bool:
        # Ensure directory exists before writing
        config_dir = self._ensure_user_config_dir()
        if not config_dir.exists():
            self.status.log(
                f"Config directory {config_dir} does not exist and could not be created",
                "ERROR",
            )
            return False

        config_file = config_dir / "crush.json"

        # Initialize Crush configuration with schema
        config_data = {"$schema": "https://charm.land/crush.json", "providers": {}}

        # Determine the default provider from the default model
        default_provider_name = None
        if cubbi_config.defaults.model:
            default_provider_name = cubbi_config.defaults.model.split("/", 1)[0]

        # Get all configured providers using the new provider system
        self.status.log(
            f"Found {len(cubbi_config.providers)} configured providers for Crush"
        )

        for provider_name, provider_config in cubbi_config.providers.items():
            is_default_provider = provider_name == default_provider_name
            crush_provider = self._map_provider_to_crush_format(
                provider_name, provider_config, is_default_provider
            )
            if crush_provider:
                # Translate google provider name to gemini for crush configuration
                crush_provider_name = (
                    "gemini" if provider_config.type == "google" else provider_name
                )
                config_data["providers"][crush_provider_name] = crush_provider
                self.status.log(
                    f"Added {crush_provider_name} provider to Crush configuration{'(default)' if is_default_provider else ''}"
                )

        if cubbi_config.defaults.model:
            provider_part, model_part = cubbi_config.defaults.model.split("/", 1)
            config_data["models"] = {
                "large": {"provider": provider_part, "model": model_part},
                "small": {"provider": provider_part, "model": model_part},
            }
            self.status.log(f"Set default model to {cubbi_config.defaults.model}")

            # add model to the crush provider only if custom
            provider = cubbi_config.providers.get(provider_part)
            if provider and provider.base_url:
                config_data["providers"][provider_part]["models"].append(
                    {"id": model_part, "name": model_part}
                )

        # Only write config if we have providers configured
        if not config_data["providers"]:
            self.status.log(
                "No providers configured, skipping Crush configuration file creation"
            )
            return True

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            self.status.log(
                f"Created Crush configuration at {config_file} with {len(config_data['providers'])} providers"
            )
            return True
        except Exception as e:
            self.status.log(f"Failed to write Crush configuration: {e}", "ERROR")
            return False

    def integrate_mcp_servers(self) -> bool:
        if not cubbi_config.mcps:
            self.status.log("No MCP servers to integrate")
            return True

        # Ensure directory exists before writing
        config_dir = self._ensure_user_config_dir()
        if not config_dir.exists():
            self.status.log(
                f"Config directory {config_dir} does not exist and could not be created",
                "ERROR",
            )
            return False

        config_file = config_dir / "crush.json"

        if config_file.exists():
            try:
                with config_file.open("r") as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                self.status.log(f"Failed to load existing config: {e}", "WARNING")
                config_data = {
                    "$schema": "https://charm.land/crush.json",
                    "providers": {},
                }
        else:
            config_data = {"$schema": "https://charm.land/crush.json", "providers": {}}

        # Crush uses "mcps" field for MCP server configuration
        if "mcps" not in config_data:
            config_data["mcps"] = {}

        for mcp in cubbi_config.mcps:
            if mcp.type == "remote":
                if mcp.name and mcp.url:
                    self.status.log(f"Adding remote MCP server: {mcp.name} - {mcp.url}")
                    config_data["mcps"][mcp.name] = {
                        "transport": {"type": "sse", "url": mcp.url},
                        "enabled": True,
                    }
            elif mcp.type in ["docker", "proxy"]:
                if mcp.name and mcp.host:
                    mcp_port = mcp.port or 8080
                    mcp_url = f"http://{mcp.host}:{mcp_port}/sse"
                    self.status.log(f"Adding MCP server: {mcp.name} - {mcp_url}")
                    config_data["mcps"][mcp.name] = {
                        "transport": {"type": "sse", "url": mcp_url},
                        "enabled": True,
                    }

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            self.status.log(
                f"Integrated {len(cubbi_config.mcps)} MCP servers into Crush configuration"
            )
            return True
        except Exception as e:
            self.status.log(f"Failed to integrate MCP servers: {e}", "ERROR")
            return False
