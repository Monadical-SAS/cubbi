#!/usr/bin/env python3
"""
Opencode-specific plugin for Cubbi initialization
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from cubbi_init import ToolPlugin

# Map of environment variables to provider names in auth.json
API_KEY_MAPPINGS = {
    "ANTHROPIC_API_KEY": "anthropic",
    "GOOGLE_API_KEY": "google",
    "OPENAI_API_KEY": "openai",
    "OPENROUTER_API_KEY": "openrouter",
}


class OpencodePlugin(ToolPlugin):
    """Plugin for Opencode AI tool initialization"""

    @property
    def tool_name(self) -> str:
        return "opencode"

    def _get_user_ids(self) -> tuple[int, int]:
        """Get the cubbi user and group IDs from environment"""
        user_id = int(os.environ.get("CUBBI_USER_ID", "1000"))
        group_id = int(os.environ.get("CUBBI_GROUP_ID", "1000"))
        return user_id, group_id

    def _set_ownership(self, path: Path) -> None:
        """Set ownership of a path to the cubbi user"""
        user_id, group_id = self._get_user_ids()
        try:
            os.chown(path, user_id, group_id)
        except OSError as e:
            self.status.log(f"Failed to set ownership for {path}: {e}", "WARNING")

    def _get_user_config_path(self) -> Path:
        """Get the correct config path for the cubbi user"""
        return Path("/home/cubbi/.config/opencode")

    def _get_user_data_path(self) -> Path:
        """Get the correct data path for the cubbi user"""
        return Path("/home/cubbi/.local/share/opencode")

    def _ensure_user_config_dir(self) -> Path:
        """Ensure config directory exists with correct ownership"""
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
        """Ensure data directory exists with correct ownership"""
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

    def _create_auth_file(self) -> bool:
        """Create auth.json file with configured API keys"""
        # Ensure data directory exists
        data_dir = self._ensure_user_data_dir()
        if not data_dir.exists():
            self.status.log(
                f"Data directory {data_dir} does not exist and could not be created",
                "ERROR",
            )
            return False

        auth_file = data_dir / "auth.json"
        auth_data = {}

        # Check each API key and add to auth data if present
        for env_var, provider in API_KEY_MAPPINGS.items():
            api_key = os.environ.get(env_var)
            if api_key:
                auth_data[provider] = {"type": "api", "key": api_key}

                # Add custom endpoint URL for OpenAI if available
                if provider == "openai":
                    openai_url = os.environ.get("OPENAI_URL")
                    if openai_url:
                        auth_data[provider]["baseURL"] = openai_url
                        self.status.log(
                            f"Added OpenAI custom endpoint URL: {openai_url}"
                        )

                self.status.log(f"Added {provider} API key to auth configuration")

        # Only write file if we have at least one API key
        if not auth_data:
            self.status.log("No API keys found, skipping auth.json creation")
            return True

        try:
            with auth_file.open("w") as f:
                json.dump(auth_data, f, indent=2)

            # Set ownership of the auth file to cubbi user
            self._set_ownership(auth_file)

            # Set secure permissions (readable only by owner)
            auth_file.chmod(0o600)

            self.status.log(f"Created OpenCode auth configuration at {auth_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to create auth configuration: {e}", "ERROR")
            return False

    def initialize(self) -> bool:
        """Initialize Opencode configuration"""
        self._ensure_user_config_dir()

        # Create auth.json file with API keys
        auth_success = self._create_auth_file()

        # Set up tool configuration
        config_success = self.setup_tool_configuration()

        return auth_success and config_success

    def setup_tool_configuration(self) -> bool:
        """Set up Opencode configuration file"""
        # Ensure directory exists before writing
        config_dir = self._ensure_user_config_dir()
        if not config_dir.exists():
            self.status.log(
                f"Config directory {config_dir} does not exist and could not be created",
                "ERROR",
            )
            return False

        config_file = config_dir / "config.json"

        # Load or initialize configuration
        if config_file.exists():
            with config_file.open("r") as f:
                config_data = json.load(f) or {}
        else:
            config_data = {}

        # Update with environment variables
        opencode_model = os.environ.get("CUBBI_MODEL")
        opencode_provider = os.environ.get("CUBBI_PROVIDER")

        if opencode_model and opencode_provider:
            config_data["model"] = f"{opencode_provider}/{opencode_model}"
            self.status.log(f"Set model to {config_data['model']}")

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            self.status.log(f"Updated Opencode configuration at {config_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Opencode configuration: {e}", "ERROR")
            return False

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate Opencode with available MCP servers"""
        if mcp_config["count"] == 0:
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

        for server in mcp_config["servers"]:
            server_name = server["name"]
            server_host = server.get("host")
            server_url = server.get("url")

            if server_name and server_host:
                mcp_url = f"http://{server_host}:8080/sse"
                self.status.log(f"Adding MCP extension: {server_name} - {mcp_url}")

                config_data["mcp"][server_name] = {
                    "type": "remote",
                    "url": mcp_url,
                }
            elif server_name and server_url:
                self.status.log(
                    f"Adding remote MCP extension: {server_name} - {server_url}"
                )

                config_data["mcp"][server_name] = {
                    "type": "remote",
                    "url": server_url,
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
