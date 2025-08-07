#!/usr/bin/env python3

import json
import os
from pathlib import Path

from cubbi_init import ToolPlugin, cubbi_config

# Standard providers that OpenCode supports natively
STANDARD_PROVIDERS = ["anthropic", "openai", "google", "openrouter"]


class OpencodePlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "opencode"

    def _get_user_ids(self) -> tuple[int, int]:
        return cubbi_config.user.uid, cubbi_config.user.gid

    def _set_ownership(self, path: Path) -> None:
        user_id, group_id = self._get_user_ids()
        try:
            os.chown(path, user_id, group_id)
        except OSError as e:
            self.status.log(f"Failed to set ownership for {path}: {e}", "WARNING")

    def _get_user_config_path(self) -> Path:
        return Path("/home/cubbi/.config/opencode")

    def _get_user_data_path(self) -> Path:
        return Path("/home/cubbi/.local/share/opencode")

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

    def _ensure_user_data_dir(self) -> Path:
        data_dir = self._get_user_data_path()

        # Create the full directory path
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            # Directory already exists, which is fine
            pass
        except OSError as e:
            self.status.log(f"Failed to create data directory {data_dir}: {e}", "ERROR")
            return data_dir

        # Set ownership for the directories
        data_parent = data_dir.parent
        if data_parent.exists():
            self._set_ownership(data_parent)

        if data_dir.exists():
            self._set_ownership(data_dir)

        return data_dir

    def initialize(self) -> bool:
        self._ensure_user_config_dir()

        # Set up tool configuration with new provider format
        config_success = self.setup_tool_configuration()

        return config_success

    def setup_tool_configuration(self) -> bool:
        # Ensure directory exists before writing
        config_dir = self._ensure_user_config_dir()
        if not config_dir.exists():
            self.status.log(
                f"Config directory {config_dir} does not exist and could not be created",
                "ERROR",
            )
            return False

        config_file = config_dir / "config.json"

        # Initialize configuration with schema
        config_data = {"$schema": "https://opencode.ai/config.json"}

        # Set default theme to system
        config_data["theme"] = "system"

        # Add providers configuration
        config_data["provider"] = {}

        # Configure all available providers
        for provider_name, provider_config in cubbi_config.providers.items():
            # Check if this is a custom provider (has baseURL)
            if provider_config.base_url:
                # Custom provider - include baseURL and name
                provider_entry = {
                    "options": {
                        "apiKey": provider_config.api_key,
                        "baseURL": provider_config.base_url,
                    },
                    "models": {},
                }

                # Add npm package and name for custom providers
                if provider_config.type in STANDARD_PROVIDERS:
                    # Standard provider with custom URL - determine npm package
                    if provider_config.type == "anthropic":
                        provider_entry["npm"] = "@ai-sdk/anthropic"
                        provider_entry["name"] = f"Anthropic ({provider_name})"
                    elif provider_config.type == "openai":
                        provider_entry["npm"] = "@ai-sdk/openai-compatible"
                        provider_entry["name"] = f"OpenAI Compatible ({provider_name})"
                    elif provider_config.type == "google":
                        provider_entry["npm"] = "@ai-sdk/google"
                        provider_entry["name"] = f"Google ({provider_name})"
                    elif provider_config.type == "openrouter":
                        provider_entry["npm"] = "@ai-sdk/openai-compatible"
                        provider_entry["name"] = f"OpenRouter ({provider_name})"
                else:
                    # Non-standard provider with custom URL
                    provider_entry["npm"] = "@ai-sdk/openai-compatible"
                    provider_entry["name"] = provider_name.title()

                config_data["provider"][provider_name] = provider_entry
                self.status.log(
                    f"Added {provider_name} custom provider to OpenCode configuration"
                )
            else:
                # Standard provider without custom URL - minimal config
                if provider_config.type in STANDARD_PROVIDERS:
                    config_data["provider"][provider_name] = {
                        "options": {"apiKey": provider_config.api_key},
                        "models": {},
                    }
                    self.status.log(
                        f"Added {provider_name} standard provider to OpenCode configuration"
                    )

        # Set default model and add it only to the default provider
        if cubbi_config.defaults.model:
            config_data["model"] = cubbi_config.defaults.model
            self.status.log(f"Set default model to {config_data['model']}")

            # Add the specific model only to the provider that matches the default model
            provider_name, model_name = cubbi_config.defaults.model.split("/", 1)
            if provider_name in config_data["provider"]:
                config_data["provider"][provider_name]["models"] = {
                    model_name: {"name": model_name}
                }
                self.status.log(
                    f"Added default model {model_name} to {provider_name} provider"
                )
        else:
            # Fallback to legacy environment variables
            opencode_model = os.environ.get("CUBBI_MODEL")
            opencode_provider = os.environ.get("CUBBI_PROVIDER")

            if opencode_model and opencode_provider:
                config_data["model"] = f"{opencode_provider}/{opencode_model}"
                self.status.log(f"Set model to {config_data['model']} (legacy)")

                # Add the legacy model to the provider if it exists
                if opencode_provider in config_data["provider"]:
                    config_data["provider"][opencode_provider]["models"] = {
                        opencode_model: {"name": opencode_model}
                    }

        # Only write config if we have providers configured
        if not config_data["provider"]:
            self.status.log(
                "No providers configured, using minimal OpenCode configuration"
            )
            config_data = {
                "$schema": "https://opencode.ai/config.json",
                "theme": "system",
            }

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            self.status.log(
                f"Updated OpenCode configuration at {config_file} with {len(config_data.get('provider', {}))} providers"
            )
            return True
        except Exception as e:
            self.status.log(f"Failed to write OpenCode configuration: {e}", "ERROR")
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

        config_file = config_dir / "config.json"

        if config_file.exists():
            with config_file.open("r") as f:
                config_data = json.load(f) or {}
        else:
            config_data = {}

        if "mcp" not in config_data:
            config_data["mcp"] = {}

        for mcp in cubbi_config.mcps:
            if mcp.type == "remote":
                if mcp.name and mcp.url:
                    self.status.log(
                        f"Adding remote MCP extension: {mcp.name} - {mcp.url}"
                    )
                    config_data["mcp"][mcp.name] = {
                        "type": "remote",
                        "url": mcp.url,
                    }
            elif mcp.type in ["docker", "proxy"]:
                if mcp.name and mcp.host:
                    mcp_port = mcp.port or 8080
                    mcp_url = f"http://{mcp.host}:{mcp_port}/sse"
                    self.status.log(f"Adding MCP extension: {mcp.name} - {mcp_url}")
                    config_data["mcp"][mcp.name] = {
                        "type": "remote",
                        "url": mcp_url,
                    }

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            return True
        except Exception as e:
            self.status.log(f"Failed to integrate MCP servers: {e}", "ERROR")
            return False
