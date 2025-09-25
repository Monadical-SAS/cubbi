#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Any

from cubbi_init import ToolPlugin, cubbi_config, set_ownership

STANDARD_PROVIDERS = ["anthropic", "openai", "google", "openrouter"]


class CrushPlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "crush"

    def _get_user_config_path(self) -> Path:
        return Path("/home/cubbi/.config/crush")

    def is_already_configured(self) -> bool:
        config_file = self._get_user_config_path() / "crush.json"
        return config_file.exists()

    def configure(self) -> bool:
        return self._setup_tool_configuration() and self._integrate_mcp_servers()

    def _map_provider_to_crush_format(
        self, provider_name: str, provider_config, is_default_provider: bool = False
    ) -> dict[str, Any] | None:
        # Handle standard providers without base_url
        if not provider_config.base_url:
            if provider_config.type in STANDARD_PROVIDERS:
                # Populate models for any standard provider that has models
                models_list = []
                if provider_config.models:
                    for model in provider_config.models:
                        model_id = model.get("id", "")
                        if model_id:
                            models_list.append({"id": model_id, "name": model_id})

                provider_entry = {
                    "api_key": provider_config.api_key,
                    "models": models_list,
                }
                return provider_entry

        # Handle custom providers with base_url
        models_list = []

        # Add all models for any provider type that has models
        if provider_config.models:
            for model in provider_config.models:
                model_id = model.get("id", "")
                if model_id:
                    models_list.append({"id": model_id, "name": model_id})

        provider_entry = {
            "api_key": provider_config.api_key,
            "base_url": provider_config.base_url,
            "models": models_list,
        }

        if provider_config.type in STANDARD_PROVIDERS:
            if provider_config.type == "anthropic":
                provider_entry["type"] = "anthropic"
            elif provider_config.type == "openai":
                provider_entry["type"] = "openai"
            elif provider_config.type == "google":
                provider_entry["type"] = "gemini"
            elif provider_config.type == "openrouter":
                provider_entry["type"] = "openai"
            provider_entry["name"] = f"{provider_name} ({provider_config.type})"
        else:
            provider_entry["type"] = "openai"
            provider_entry["name"] = f"{provider_name} ({provider_config.type})"

        return provider_entry

    def _setup_tool_configuration(self) -> bool:
        config_dir = self.create_directory_with_ownership(self._get_user_config_path())
        if not config_dir.exists():
            self.status.log(
                f"Config directory {config_dir} does not exist and could not be created",
                "ERROR",
            )
            return False

        config_file = config_dir / "crush.json"

        config_data = {"$schema": "https://charm.land/crush.json", "providers": {}}

        default_provider_name = None
        if cubbi_config.defaults.model:
            default_provider_name = cubbi_config.defaults.model.split("/", 1)[0]

        self.status.log(
            f"Found {len(cubbi_config.providers)} configured providers for Crush"
        )

        for provider_name, provider_config in cubbi_config.providers.items():
            is_default_provider = provider_name == default_provider_name
            crush_provider = self._map_provider_to_crush_format(
                provider_name, provider_config, is_default_provider
            )
            if crush_provider:
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

            provider = cubbi_config.providers.get(provider_part)
            if provider and provider.base_url:
                config_data["providers"][provider_part]["models"].append(
                    {"id": model_part, "name": model_part}
                )

        if not config_data["providers"]:
            self.status.log(
                "No providers configured, skipping Crush configuration file creation"
            )
            return True

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            set_ownership(config_file)

            self.status.log(
                f"Created Crush configuration at {config_file} with {len(config_data['providers'])} providers"
            )
            return True
        except Exception as e:
            self.status.log(f"Failed to write Crush configuration: {e}", "ERROR")
            return False

    def _integrate_mcp_servers(self) -> bool:
        if not cubbi_config.mcps:
            self.status.log("No MCP servers to integrate")
            return True

        config_dir = self.create_directory_with_ownership(self._get_user_config_path())
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
            elif mcp.type == "local":
                if mcp.name and mcp.command:
                    self.status.log(
                        f"Adding local MCP server: {mcp.name} - {mcp.command}"
                    )
                    # Crush uses stdio type for local MCPs
                    transport_config = {
                        "type": "stdio",
                        "command": mcp.command,
                    }
                    if mcp.args:
                        transport_config["args"] = mcp.args
                    if mcp.env:
                        transport_config["env"] = mcp.env
                    config_data["mcps"][mcp.name] = {
                        "transport": transport_config,
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

            set_ownership(config_file)

            self.status.log(
                f"Integrated {len(cubbi_config.mcps)} MCP servers into Crush configuration"
            )
            return True
        except Exception as e:
            self.status.log(f"Failed to integrate MCP servers: {e}", "ERROR")
            return False


PLUGIN_CLASS = CrushPlugin
