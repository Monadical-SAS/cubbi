#!/usr/bin/env python3
"""
Gemini CLI Plugin for Cubbi
Handles authentication setup and configuration for Google Gemini CLI
"""

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict

from cubbi_init import ToolPlugin


class GeminiCliPlugin(ToolPlugin):
    """Plugin for setting up Gemini CLI authentication and configuration"""

    @property
    def tool_name(self) -> str:
        return "gemini-cli"

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

    def _get_gemini_config_dir(self) -> Path:
        """Get the Gemini configuration directory"""
        # Get the actual username from the config if available
        username = self.config.get("username", "cubbi")
        return Path(f"/home/{username}/.config/gemini")

    def _get_gemini_cache_dir(self) -> Path:
        """Get the Gemini cache directory"""
        # Get the actual username from the config if available
        username = self.config.get("username", "cubbi")
        return Path(f"/home/{username}/.cache/gemini")

    def _ensure_gemini_dirs(self) -> tuple[Path, Path]:
        """Ensure Gemini directories exist with correct ownership"""
        config_dir = self._get_gemini_config_dir()
        cache_dir = self._get_gemini_cache_dir()

        # Create directories
        for directory in [config_dir, cache_dir]:
            try:
                directory.mkdir(mode=0o755, parents=True, exist_ok=True)
                self._set_ownership(directory)
            except OSError as e:
                self.status.log(
                    f"Failed to create Gemini directory {directory}: {e}", "ERROR"
                )

        return config_dir, cache_dir

    def initialize(self) -> bool:
        """Initialize Gemini CLI configuration"""
        self.status.log("Setting up Gemini CLI configuration...")

        # Ensure Gemini directories exist
        config_dir, cache_dir = self._ensure_gemini_dirs()

        # Set up authentication and configuration
        auth_configured = self._setup_authentication(config_dir)
        config_created = self._create_configuration_file(config_dir)

        if auth_configured or config_created:
            self.status.log("✅ Gemini CLI configured successfully")
        else:
            self.status.log(
                "ℹ️ No API key found - Gemini CLI will require authentication",
                "INFO",
            )
            self.status.log(
                "   You can configure API keys using environment variables", "INFO"
            )

        # Always return True to allow container to start
        return True

    def _setup_authentication(self, config_dir: Path) -> bool:
        """Set up Gemini authentication"""
        api_key = self._get_api_key()

        if not api_key:
            return False

        # Create environment file for API key
        env_file = config_dir / ".env"
        try:
            with open(env_file, "w") as f:
                f.write(f"GEMINI_API_KEY={api_key}\n")

            # Set ownership and secure file permissions
            self._set_ownership(env_file)
            os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

            self.status.log(f"Created Gemini environment file at {env_file}")
            self.status.log("Added Gemini API key")
            return True

        except Exception as e:
            self.status.log(f"Failed to create environment file: {e}", "ERROR")
            return False

    def _get_api_key(self) -> str:
        """Get the Gemini API key from environment variables"""
        # Check multiple possible environment variable names
        for key_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            api_key = os.environ.get(key_name)
            if api_key:
                return api_key
        return ""

    def _create_configuration_file(self, config_dir: Path) -> bool:
        """Create Gemini CLI configuration file"""
        try:
            config = self._build_configuration()

            if not config:
                return False

            config_file = config_dir / "config.json"
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)

            # Set ownership and permissions
            self._set_ownership(config_file)
            os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)

            self.status.log(f"Created Gemini configuration at {config_file}")
            return True

        except Exception as e:
            self.status.log(f"Failed to create configuration file: {e}", "ERROR")
            return False

    def _build_configuration(self) -> Dict[str, Any]:
        """Build Gemini CLI configuration from environment variables"""
        config = {}

        # Model configuration
        model = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
        if model:
            config["defaultModel"] = model
            self.status.log(f"Set default model to {model}")

        # Temperature setting
        temperature = os.environ.get("GEMINI_TEMPERATURE")
        if temperature:
            try:
                temp_value = float(temperature)
                if 0.0 <= temp_value <= 2.0:
                    config["temperature"] = temp_value
                    self.status.log(f"Set temperature to {temp_value}")
                else:
                    self.status.log(
                        f"Invalid temperature value {temperature}, using default",
                        "WARNING",
                    )
            except ValueError:
                self.status.log(
                    f"Invalid temperature format {temperature}, using default",
                    "WARNING",
                )

        # Max tokens setting
        max_tokens = os.environ.get("GEMINI_MAX_TOKENS")
        if max_tokens:
            try:
                tokens_value = int(max_tokens)
                if tokens_value > 0:
                    config["maxTokens"] = tokens_value
                    self.status.log(f"Set max tokens to {tokens_value}")
                else:
                    self.status.log(
                        f"Invalid max tokens value {max_tokens}, using default",
                        "WARNING",
                    )
            except ValueError:
                self.status.log(
                    f"Invalid max tokens format {max_tokens}, using default",
                    "WARNING",
                )

        # Search configuration
        search_enabled = os.environ.get("GEMINI_SEARCH_ENABLED", "false")
        if search_enabled.lower() in ["true", "false"]:
            config["searchEnabled"] = search_enabled.lower() == "true"
            if config["searchEnabled"]:
                self.status.log("Enabled Google Search grounding")

        # Debug mode
        debug_mode = os.environ.get("GEMINI_DEBUG", "false")
        if debug_mode.lower() in ["true", "false"]:
            config["debug"] = debug_mode.lower() == "true"
            if config["debug"]:
                self.status.log("Enabled debug mode")

        # Proxy settings
        for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY"]:
            proxy_value = os.environ.get(proxy_var)
            if proxy_value:
                config[proxy_var.lower()] = proxy_value
                self.status.log(f"Added proxy configuration: {proxy_var}")

        # Google Cloud project
        project = os.environ.get("GCLOUD_PROJECT")
        if project:
            config["project"] = project
            self.status.log(f"Set Google Cloud project to {project}")

        return config

    def setup_tool_configuration(self) -> bool:
        """Set up Gemini CLI configuration - called by base class"""
        # Additional tool configuration can be added here if needed
        return True

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate Gemini CLI with available MCP servers if applicable"""
        if mcp_config["count"] == 0:
            self.status.log("No MCP servers to integrate")
            return True

        # Gemini CLI doesn't have native MCP support,
        # but we could potentially add custom integrations here
        self.status.log(
            f"Found {mcp_config['count']} MCP server(s) - no direct integration available"
        )
        return True
