#!/usr/bin/env python3
"""
Goose-specific plugin for Cubbi initialization
"""

import os
from pathlib import Path
from typing import Any, Dict

from cubbi_init import ToolPlugin
from ruamel.yaml import YAML


class GoosePlugin(ToolPlugin):
    """Plugin for Goose AI tool initialization"""

    @property
    def tool_name(self) -> str:
        return "goose"

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
        return Path("/home/cubbi/.config/goose")

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

    def initialize(self) -> bool:
        """Initialize Goose configuration"""
        self._ensure_user_config_dir()
        return self.setup_tool_configuration()

    def setup_tool_configuration(self) -> bool:
        """Set up Goose configuration file"""
        # Ensure directory exists before writing
        config_dir = self._ensure_user_config_dir()
        if not config_dir.exists():
            self.status.log(
                f"Config directory {config_dir} does not exist and could not be created",
                "ERROR",
            )
            return False

        config_file = config_dir / "config.yaml"
        yaml = YAML(typ="safe")

        # Load or initialize configuration
        if config_file.exists():
            with config_file.open("r") as f:
                config_data = yaml.load(f) or {}
        else:
            config_data = {}

        if "extensions" not in config_data:
            config_data["extensions"] = {}

        # Add default developer extension
        config_data["extensions"]["developer"] = {
            "enabled": True,
            "name": "developer",
            "timeout": 300,
            "type": "builtin",
        }

        # Update with environment variables
        goose_model = os.environ.get("CUBBI_MODEL")
        goose_provider = os.environ.get("CUBBI_PROVIDER")

        if goose_model:
            config_data["GOOSE_MODEL"] = goose_model
            self.status.log(f"Set GOOSE_MODEL to {goose_model}")

        if goose_provider:
            config_data["GOOSE_PROVIDER"] = goose_provider
            self.status.log(f"Set GOOSE_PROVIDER to {goose_provider}")

            # If provider is OpenAI and OPENAI_URL is set, configure OPENAI_HOST
            if goose_provider.lower() == "openai":
                openai_url = os.environ.get("OPENAI_URL")
                if openai_url:
                    config_data["OPENAI_HOST"] = openai_url
                    self.status.log(f"Set OPENAI_HOST to {openai_url}")

        try:
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            self.status.log(f"Updated Goose configuration at {config_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Goose configuration: {e}", "ERROR")
            return False

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate Goose with available MCP servers"""
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

        config_file = config_dir / "config.yaml"
        yaml = YAML(typ="safe")

        if config_file.exists():
            with config_file.open("r") as f:
                config_data = yaml.load(f) or {}
        else:
            config_data = {"extensions": {}}

        if "extensions" not in config_data:
            config_data["extensions"] = {}

        for server in mcp_config["servers"]:
            server_name = server["name"]
            server_host = server["host"]
            server_url = server["url"]

            if server_name and server_host:
                mcp_url = f"http://{server_host}:8080/sse"
                self.status.log(f"Adding MCP extension: {server_name} - {mcp_url}")

                config_data["extensions"][server_name] = {
                    "enabled": True,
                    "name": server_name,
                    "timeout": 60,
                    "type": "sse",
                    "uri": mcp_url,
                    "envs": {},
                }
            elif server_name and server_url:
                self.status.log(
                    f"Adding remote MCP extension: {server_name} - {server_url}"
                )

                config_data["extensions"][server_name] = {
                    "enabled": True,
                    "name": server_name,
                    "timeout": 60,
                    "type": "sse",
                    "uri": server_url,
                    "envs": {},
                }

        try:
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            return True
        except Exception as e:
            self.status.log(f"Failed to integrate MCP servers: {e}", "ERROR")
            return False
