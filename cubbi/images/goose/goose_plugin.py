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

    def initialize(self) -> bool:
        """Initialize Goose configuration"""
        config_dir = Path.home() / ".config/goose"
        config_dir.mkdir(parents=True, exist_ok=True)

        return self.setup_tool_configuration()

    def setup_tool_configuration(self) -> bool:
        """Set up Goose configuration file"""
        config_file = Path.home() / ".config/goose/config.yaml"
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

        try:
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

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

        config_file = Path.home() / ".config/goose/config.yaml"
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

            return True
        except Exception as e:
            self.status.log(f"Failed to integrate MCP servers: {e}", "ERROR")
            return False
