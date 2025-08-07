#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Any, Dict

from cubbi_init import ToolPlugin, cubbi_config


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
        self, provider_name: str, provider_config
    ) -> Dict[str, Any] | None:
        """Map cubbi provider configuration to crush provider format"""

        if provider_config.type == "anthropic":
            return {
                "name": "Anthropic",
                "type": "anthropic",
                "api_key": provider_config.api_key,
                "base_url": provider_config.base_url or "https://api.anthropic.com/v1",
                "models": [
                    {
                        "id": "claude-3-5-sonnet-20241022",
                        "name": "Claude 3.5 Sonnet",
                        "context_window": 200000,
                        "default_max_tokens": 4096,
                    },
                    {
                        "id": "claude-3-5-haiku-20241022",
                        "name": "Claude 3.5 Haiku",
                        "context_window": 200000,
                        "default_max_tokens": 4096,
                    },
                ],
            }

        elif provider_config.type == "openai":
            base_url = provider_config.base_url or "https://api.openai.com/v1"
            return {
                "name": "OpenAI"
                if base_url.startswith("https://api.openai.com")
                else f"OpenAI ({base_url})",
                "type": "openai",
                "api_key": provider_config.api_key,
                "base_url": base_url,
                "models": [
                    {
                        "id": "gpt-4o",
                        "name": "GPT-4o",
                        "context_window": 128000,
                        "default_max_tokens": 4096,
                    },
                    {
                        "id": "gpt-4o-mini",
                        "name": "GPT-4o Mini",
                        "context_window": 128000,
                        "default_max_tokens": 16384,
                    },
                ],
            }

        elif provider_config.type == "google":
            return {
                "name": "Google",
                "type": "openai",  # Google Gemini uses OpenAI-compatible API
                "api_key": provider_config.api_key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "models": [
                    {
                        "id": "gemini-1.5-pro",
                        "name": "Gemini 1.5 Pro",
                        "context_window": 2000000,
                        "default_max_tokens": 8192,
                    },
                    {
                        "id": "gemini-1.5-flash",
                        "name": "Gemini 1.5 Flash",
                        "context_window": 1000000,
                        "default_max_tokens": 8192,
                    },
                ],
            }

        elif provider_config.type == "openrouter":
            return {
                "name": "OpenRouter",
                "type": "openai",
                "api_key": provider_config.api_key,
                "base_url": "https://openrouter.ai/api/v1",
                "models": [
                    {
                        "id": "anthropic/claude-3.5-sonnet",
                        "name": "Claude 3.5 Sonnet (via OpenRouter)",
                        "context_window": 200000,
                        "default_max_tokens": 4096,
                    },
                    {
                        "id": "openai/gpt-4o",
                        "name": "GPT-4o (via OpenRouter)",
                        "context_window": 128000,
                        "default_max_tokens": 4096,
                    },
                ],
            }

        return None

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

        # Get all configured providers using the new provider system
        self.status.log(
            f"Found {len(cubbi_config.providers)} configured providers for Crush"
        )

        for provider_name, provider_config in cubbi_config.providers.items():
            crush_provider = self._map_provider_to_crush_format(
                provider_name, provider_config
            )
            if crush_provider:
                config_data["providers"][provider_name] = crush_provider
                self.status.log(
                    f"Added {provider_name} provider to Crush configuration"
                )

        # Fallback to legacy environment variables if no providers found
        if not config_data["providers"]:
            self.status.log(
                "No providers found via new system, falling back to legacy detection"
            )

            # Check for legacy environment variables
            legacy_providers = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "google": "GOOGLE_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
            }

            for provider_name, env_var in legacy_providers.items():
                api_key = os.environ.get(env_var)
                if api_key:
                    # Create a simple object for legacy compatibility
                    class LegacyProvider:
                        def __init__(self, provider_type, api_key, base_url=None):
                            self.type = provider_type
                            self.api_key = api_key
                            self.base_url = base_url

                    if provider_name == "openai":
                        openai_url = os.environ.get("OPENAI_URL")
                        legacy_provider = LegacyProvider("openai", api_key, openai_url)
                    else:
                        legacy_provider = LegacyProvider(provider_name, api_key)

                    crush_provider = self._map_provider_to_crush_format(
                        provider_name, legacy_provider
                    )
                    if crush_provider:
                        config_data["providers"][provider_name] = crush_provider
                        self.status.log(
                            f"Added {provider_name} provider from legacy environment (legacy)"
                        )

        # Set default model from cubbi configuration
        if cubbi_config.defaults.model:
            # Crush expects provider/model format for default model selection
            config_data["default_model"] = cubbi_config.defaults.model
            self.status.log(f"Set default model to {config_data['default_model']}")

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
