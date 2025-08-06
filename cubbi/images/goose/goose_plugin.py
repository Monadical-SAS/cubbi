#!/usr/bin/env python3

import os
from pathlib import Path

from cubbi_init import ToolPlugin, cubbi_config
from ruamel.yaml import YAML


class GoosePlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "goose"

    def _get_user_ids(self) -> tuple[int, int]:
        return cubbi_config.user.uid, cubbi_config.user.gid

    def _set_ownership(self, path: Path) -> None:
        user_id, group_id = self._get_user_ids()
        try:
            os.chown(path, user_id, group_id)
        except OSError as e:
            self.status.log(f"Failed to set ownership for {path}: {e}", "WARNING")

    def _get_user_config_path(self) -> Path:
        return Path("/home/cubbi/.config/goose")

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

        # Configure Goose with the default model
        provider_config = cubbi_config.get_provider_for_default_model()
        if provider_config and cubbi_config.defaults.model:
            _, model_name = cubbi_config.defaults.model.split("/", 1)

            # Set Goose model and provider
            config_data["GOOSE_MODEL"] = model_name
            config_data["GOOSE_PROVIDER"] = provider_config.type

            self.status.log(
                f"Configured Goose: model={model_name}, provider={provider_config.type}"
            )

            # Set base URL for OpenAI-compatible providers
            if provider_config.type == "openai" and provider_config.base_url:
                config_data["OPENAI_HOST"] = provider_config.base_url
                self.status.log(f"Set OPENAI_HOST to {provider_config.base_url}")
        else:
            self.status.log("No default model or provider configured", "WARNING")

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

        config_file = config_dir / "config.yaml"
        yaml = YAML(typ="safe")

        if config_file.exists():
            with config_file.open("r") as f:
                config_data = yaml.load(f) or {}
        else:
            config_data = {"extensions": {}}

        if "extensions" not in config_data:
            config_data["extensions"] = {}

        for mcp in cubbi_config.mcps:
            if mcp.type == "remote":
                if mcp.name and mcp.url:
                    self.status.log(
                        f"Adding remote MCP extension: {mcp.name} - {mcp.url}"
                    )
                    config_data["extensions"][mcp.name] = {
                        "enabled": True,
                        "name": mcp.name,
                        "timeout": 60,
                        "type": "sse",
                        "uri": mcp.url,
                        "envs": {},
                    }
            elif mcp.type in ["docker", "proxy"]:
                if mcp.name and mcp.host:
                    mcp_port = mcp.port or 8080
                    mcp_url = f"http://{mcp.host}:{mcp_port}/sse"
                    self.status.log(f"Adding MCP extension: {mcp.name} - {mcp_url}")
                    config_data["extensions"][mcp.name] = {
                        "enabled": True,
                        "name": mcp.name,
                        "timeout": 60,
                        "type": "sse",
                        "uri": mcp_url,
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
