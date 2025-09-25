#!/usr/bin/env python3

import os
from pathlib import Path

from cubbi_init import ToolPlugin, cubbi_config, set_ownership
from ruamel.yaml import YAML


class GoosePlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "goose"

    def is_already_configured(self) -> bool:
        config_file = Path("/home/cubbi/.config/goose/config.yaml")
        return config_file.exists()

    def configure(self) -> bool:
        self._ensure_user_config_dir()
        if not self.setup_tool_configuration():
            return False
        return self.integrate_mcp_servers()

    def _get_user_config_path(self) -> Path:
        return Path("/home/cubbi/.config/goose")

    def _ensure_user_config_dir(self) -> Path:
        config_dir = self._get_user_config_path()
        return self.create_directory_with_ownership(config_dir)

    def _write_env_vars_to_profile(self, env_vars: dict) -> None:
        try:
            profile_path = Path("/home/cubbi/.bashrc")

            env_section_start = "# CUBBI GOOSE ENVIRONMENT VARIABLES"
            env_section_end = "# END CUBBI GOOSE ENVIRONMENT VARIABLES"

            if profile_path.exists():
                with open(profile_path, "r") as f:
                    lines = f.readlines()
            else:
                lines = []

            new_lines = []
            skip_section = False
            for line in lines:
                if env_section_start in line:
                    skip_section = True
                elif env_section_end in line:
                    skip_section = False
                    continue
                elif not skip_section:
                    new_lines.append(line)

            if env_vars:
                new_lines.append(f"\n{env_section_start}\n")
                for key, value in env_vars.items():
                    new_lines.append(f'export {key}="{value}"\n')
                new_lines.append(f"{env_section_end}\n")

            profile_path.parent.mkdir(parents=True, exist_ok=True)
            with open(profile_path, "w") as f:
                f.writelines(new_lines)

            set_ownership(profile_path)

            self.status.log(
                f"Updated shell profile with {len(env_vars)} environment variables"
            )

        except Exception as e:
            self.status.log(
                f"Failed to write environment variables to profile: {e}", "ERROR"
            )

    def setup_tool_configuration(self) -> bool:
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

            # Set ONLY the specific API key for the selected provider
            # Set both in current process AND in shell environment file
            env_vars_to_set = {}

            if provider_config.type == "anthropic" and provider_config.api_key:
                env_vars_to_set["ANTHROPIC_API_KEY"] = provider_config.api_key
                self.status.log("Set Anthropic API key for goose")
            elif provider_config.type == "openai" and provider_config.api_key:
                # For OpenAI-compatible providers (including litellm), goose expects OPENAI_API_KEY
                env_vars_to_set["OPENAI_API_KEY"] = provider_config.api_key
                self.status.log("Set OpenAI API key for goose")
                # Set base URL for OpenAI-compatible providers in both env and config
                if provider_config.base_url:
                    env_vars_to_set["OPENAI_BASE_URL"] = provider_config.base_url
                    config_data["OPENAI_HOST"] = provider_config.base_url
                    self.status.log(
                        f"Set OPENAI_BASE_URL and OPENAI_HOST to {provider_config.base_url}"
                    )
            elif provider_config.type == "google" and provider_config.api_key:
                env_vars_to_set["GOOGLE_API_KEY"] = provider_config.api_key
                self.status.log("Set Google API key for goose")
            elif provider_config.type == "openrouter" and provider_config.api_key:
                env_vars_to_set["OPENROUTER_API_KEY"] = provider_config.api_key
                self.status.log("Set OpenRouter API key for goose")

            # Set environment variables for current process (for --run commands)
            for key, value in env_vars_to_set.items():
                os.environ[key] = value

            # Write environment variables to shell profile for interactive sessions
            self._write_env_vars_to_profile(env_vars_to_set)

            self.status.log(
                f"Configured Goose: model={model_name}, provider={provider_config.type}"
            )
        else:
            self.status.log("No default model or provider configured", "WARNING")

        try:
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

            set_ownership(config_file)

            self.status.log(f"Updated Goose configuration at {config_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Goose configuration: {e}", "ERROR")
            return False

    def integrate_mcp_servers(self) -> bool:
        if not cubbi_config.mcps:
            self.status.log("No MCP servers to integrate")
            return True

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
            elif mcp.type == "local":
                if mcp.name and mcp.command:
                    self.status.log(
                        f"Adding local MCP extension: {mcp.name} - {mcp.command}"
                    )
                    # Goose uses stdio type for local MCPs
                    config_data["extensions"][mcp.name] = {
                        "enabled": True,
                        "name": mcp.name,
                        "timeout": 60,
                        "type": "stdio",
                        "command": mcp.command,
                        "args": mcp.args if mcp.args else [],
                        "envs": mcp.env if mcp.env else {},
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

            set_ownership(config_file)

            return True
        except Exception as e:
            self.status.log(f"Failed to integrate MCP servers: {e}", "ERROR")
            return False


PLUGIN_CLASS = GoosePlugin
