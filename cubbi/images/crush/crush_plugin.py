#!/usr/bin/env python3
"""
Crush-specific plugin for Cubbi initialization
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from cubbi_init import ToolPlugin


class CrushPlugin(ToolPlugin):
    """Plugin for Crush AI coding assistant initialization"""

    @property
    def tool_name(self) -> str:
        return "crush"

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
        return Path("/home/cubbi/.config/crush")

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
        """Initialize Crush configuration"""
        self._ensure_user_config_dir()
        return self.setup_tool_configuration()

    def setup_tool_configuration(self) -> bool:
        """Set up Crush configuration file"""
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
            try:
                with config_file.open("r") as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                self.status.log(f"Failed to load existing config: {e}", "WARNING")
                config_data = {}
        else:
            config_data = {}

        # Set default model and provider if specified
        # cubbi_model = os.environ.get("CUBBI_MODEL")
        # cubbi_provider = os.environ.get("CUBBI_PROVIDER")
        # XXX i didn't understood yet the configuration file, tbd later.

        try:
            with config_file.open("w") as f:
                json.dump(config_data, f, indent=2)

            # Set ownership of the config file to cubbi user
            self._set_ownership(config_file)

            self.status.log(f"Updated Crush configuration at {config_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Crush configuration: {e}", "ERROR")
            return False

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate Crush with available MCP servers"""
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
            try:
                with config_file.open("r") as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                self.status.log(f"Failed to load existing config: {e}", "WARNING")
                config_data = {}
        else:
            config_data = {}

        if "mcp_servers" not in config_data:
            config_data["mcp_servers"] = {}

        for server in mcp_config["servers"]:
            server_name = server["name"]
            server_host = server["host"]
            server_url = server["url"]

            if server_name and server_host:
                mcp_url = f"http://{server_host}:8080/sse"
                self.status.log(f"Adding MCP server: {server_name} - {mcp_url}")

                config_data["mcp_servers"][server_name] = {
                    "uri": mcp_url,
                    "type": server.get("type", "sse"),
                    "enabled": True,
                }
            elif server_name and server_url:
                self.status.log(
                    f"Adding remote MCP server: {server_name} - {server_url}"
                )

                config_data["mcp_servers"][server_name] = {
                    "uri": server_url,
                    "type": server.get("type", "sse"),
                    "enabled": True,
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
