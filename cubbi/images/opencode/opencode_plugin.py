#!/usr/bin/env python3

import json
import os
from pathlib import Path

from cubbi_init import ToolPlugin, cubbi_config, set_ownership

# Standard providers that OpenCode supports natively
STANDARD_PROVIDERS: list[str] = ["anthropic", "openai", "google", "openrouter"]


class OpencodePlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "opencode"

    def _get_user_config_path(self) -> Path:
        return Path("/home/cubbi/.config/opencode")

    def is_already_configured(self) -> bool:
        config_file = self._get_user_config_path() / "config.json"
        return config_file.exists()

    def configure(self) -> bool:
        self.create_directory_with_ownership(self._get_user_config_path())

        config_success = self.setup_tool_configuration()
        if not config_success:
            return False

        return self.integrate_mcp_servers()

    def setup_tool_configuration(self) -> bool:
        config_dir = self._get_user_config_path()
        config_file = config_dir / "config.json"

        # Initialize configuration with schema
        config_data: dict[str, str | dict[str, dict[str, str | dict[str, str]]]] = {
            "$schema": "https://opencode.ai/config.json"
        }

        # Set default theme to system
        config_data["theme"] = "system"

        # Add providers configuration
        config_data["provider"] = {}

        # Configure all available providers
        for provider_name, provider_config in cubbi_config.providers.items():
            # Check if this is a custom provider (has baseURL)
            if provider_config.base_url:
                # Custom provider - include baseURL and name
                models_dict = {}

                # Add all models for any provider type that has models
                if provider_config.models:
                    for model in provider_config.models:
                        model_id = model.get("id", "")
                        if model_id:
                            models_dict[model_id] = {"name": model_id}

                provider_entry: dict[str, str | dict[str, str]] = {
                    "options": {
                        "apiKey": provider_config.api_key,
                        "baseURL": provider_config.base_url,
                    },
                    "models": models_dict,
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
                if models_dict:
                    self.status.log(
                        f"Added {provider_name} custom provider with {len(models_dict)} models to OpenCode configuration"
                    )
                else:
                    self.status.log(
                        f"Added {provider_name} custom provider to OpenCode configuration"
                    )
            else:
                # Standard provider without custom URL
                if provider_config.type in STANDARD_PROVIDERS:
                    # Populate models for any provider that has models
                    models_dict = {}
                    if provider_config.models:
                        for model in provider_config.models:
                            model_id = model.get("id", "")
                            if model_id:
                                models_dict[model_id] = {"name": model_id}

                    config_data["provider"][provider_name] = {
                        "options": {"apiKey": provider_config.api_key},
                        "models": models_dict,
                    }

                    if models_dict:
                        self.status.log(
                            f"Added {provider_name} standard provider with {len(models_dict)} models to OpenCode configuration"
                        )
                    else:
                        self.status.log(
                            f"Added {provider_name} standard provider to OpenCode configuration"
                        )

        # Set default model
        if cubbi_config.defaults.model:
            config_data["model"] = cubbi_config.defaults.model
            self.status.log(f"Set default model to {config_data['model']}")

            # Add the default model to provider if it doesn't already have models
            provider_name: str
            model_name: str
            provider_name, model_name = cubbi_config.defaults.model.split("/", 1)
            if provider_name in config_data["provider"]:
                provider_config = cubbi_config.providers.get(provider_name)
                # Only add default model if provider doesn't already have models populated
                if not (provider_config and provider_config.models):
                    config_data["provider"][provider_name]["models"] = {
                        model_name: {"name": model_name}
                    }
                    self.status.log(
                        f"Added default model {model_name} to {provider_name} provider"
                    )
        else:
            # Fallback to legacy environment variables
            opencode_model: str | None = os.environ.get("CUBBI_MODEL")
            opencode_provider: str | None = os.environ.get("CUBBI_PROVIDER")

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

            set_ownership(config_file)

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

        config_dir = self._get_user_config_path()
        config_file = config_dir / "config.json"

        if config_file.exists():
            with config_file.open("r") as f:
                config_data: dict[str, str | dict[str, dict[str, str]]] = (
                    json.load(f) or {}
                )
        else:
            config_data: dict[str, str | dict[str, dict[str, str]]] = {}

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
            elif mcp.type == "local":
                if mcp.name and mcp.command:
                    self.status.log(
                        f"Adding local MCP extension: {mcp.name} - {mcp.command}"
                    )
                    # OpenCode expects command as an array with command and args combined
                    command_array = [mcp.command]
                    if mcp.args:
                        command_array.extend(mcp.args)

                    mcp_entry: dict[str, str | list[str] | bool | dict[str, str]] = {
                        "type": "local",
                        "command": command_array,
                        "enabled": True,
                    }
                    if mcp.env:
                        # OpenCode expects environment (not env)
                        mcp_entry["environment"] = mcp.env
                    config_data["mcp"][mcp.name] = mcp_entry
            elif mcp.type in ["docker", "proxy"]:
                if mcp.name and mcp.host:
                    mcp_port: int = mcp.port or 8080
                    mcp_url: str = f"http://{mcp.host}:{mcp_port}/sse"
                    self.status.log(f"Adding MCP extension: {mcp.name} - {mcp_url}")
                    config_data["mcp"][mcp.name] = {
                        "type": "remote",
                        "url": mcp_url,
                    }

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            set_ownership(config_file)

            return True
        except Exception as e:
            self.status.log(f"Failed to integrate MCP servers: {e}", "ERROR")
            return False


PLUGIN_CLASS = OpencodePlugin
