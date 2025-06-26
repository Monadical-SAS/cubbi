#!/usr/bin/env python3
"""
Aider Plugin for Cubbi
Handles authentication setup and configuration for Aider AI pair programming
"""

import os
import stat
from pathlib import Path
from typing import Any, Dict

from cubbi_init import ToolPlugin


class AiderPlugin(ToolPlugin):
    """Plugin for setting up Aider authentication and configuration"""

    @property
    def tool_name(self) -> str:
        return "aider"

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

    def _get_aider_config_dir(self) -> Path:
        """Get the Aider configuration directory"""
        return Path("/home/cubbi/.aider")

    def _get_aider_cache_dir(self) -> Path:
        """Get the Aider cache directory"""
        return Path("/home/cubbi/.cache/aider")

    def _ensure_aider_dirs(self) -> tuple[Path, Path]:
        """Ensure Aider directories exist with correct ownership"""
        config_dir = self._get_aider_config_dir()
        cache_dir = self._get_aider_cache_dir()

        # Create directories
        for directory in [config_dir, cache_dir]:
            try:
                directory.mkdir(mode=0o755, parents=True, exist_ok=True)
                self._set_ownership(directory)
            except OSError as e:
                self.status.log(
                    f"Failed to create Aider directory {directory}: {e}", "ERROR"
                )

        return config_dir, cache_dir

    def initialize(self) -> bool:
        """Initialize Aider configuration"""
        self.status.log("Setting up Aider configuration...")

        # Ensure Aider directories exist
        config_dir, cache_dir = self._ensure_aider_dirs()

        # Set up environment variables for the session
        env_vars = self._create_environment_config()

        # Create .env file if we have API keys
        if env_vars:
            env_file = config_dir / ".env"
            success = self._write_env_file(env_file, env_vars)
            if success:
                self.status.log("✅ Aider environment configured successfully")
            else:
                self.status.log("⚠️ Failed to write Aider environment file", "WARNING")
        else:
            self.status.log(
                "ℹ️ No API keys found - Aider will run without pre-configuration", "INFO"
            )
            self.status.log(
                "   You can configure API keys later using environment variables",
                "INFO",
            )

        # Always return True to allow container to start
        return True

    def _create_environment_config(self) -> Dict[str, str]:
        """Create environment variable configuration for Aider"""
        env_vars = {}

        # Map environment variables to Aider configuration
        api_key_mappings = {
            "OPENAI_API_KEY": "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
            "DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
            "GEMINI_API_KEY": "GEMINI_API_KEY",
            "OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
        }

        # Check for standard API keys
        for env_var, aider_var in api_key_mappings.items():
            value = os.environ.get(env_var)
            if value:
                env_vars[aider_var] = value
                provider = env_var.replace("_API_KEY", "").lower()
                self.status.log(f"Added {provider} API key")

        # Handle additional API keys from AIDER_API_KEYS
        additional_keys = os.environ.get("AIDER_API_KEYS")
        if additional_keys:
            try:
                # Parse format: "provider1=key1,provider2=key2"
                for pair in additional_keys.split(","):
                    if "=" in pair:
                        provider, key = pair.strip().split("=", 1)
                        env_var_name = f"{provider.upper()}_API_KEY"
                        env_vars[env_var_name] = key
                        self.status.log(f"Added {provider} API key from AIDER_API_KEYS")
            except Exception as e:
                self.status.log(f"Failed to parse AIDER_API_KEYS: {e}", "WARNING")

        # Add model configuration
        model = os.environ.get("AIDER_MODEL")
        if model:
            env_vars["AIDER_MODEL"] = model
            self.status.log(f"Set default model to {model}")

        # Add git configuration
        auto_commits = os.environ.get("AIDER_AUTO_COMMITS", "true")
        if auto_commits.lower() in ["true", "false"]:
            env_vars["AIDER_AUTO_COMMITS"] = auto_commits

        # Add dark mode setting
        dark_mode = os.environ.get("AIDER_DARK_MODE", "false")
        if dark_mode.lower() in ["true", "false"]:
            env_vars["AIDER_DARK_MODE"] = dark_mode

        # Add proxy settings
        for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY"]:
            value = os.environ.get(proxy_var)
            if value:
                env_vars[proxy_var] = value
                self.status.log(f"Added proxy configuration: {proxy_var}")

        return env_vars

    def _write_env_file(self, env_file: Path, env_vars: Dict[str, str]) -> bool:
        """Write environment variables to .env file"""
        try:
            content = "\n".join(f"{key}={value}" for key, value in env_vars.items())

            with open(env_file, "w") as f:
                f.write(content)
                f.write("\n")

            # Set ownership and secure file permissions (read/write for owner only)
            self._set_ownership(env_file)
            os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

            self.status.log(f"Created Aider environment file at {env_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Aider environment file: {e}", "ERROR")
            return False

    def setup_tool_configuration(self) -> bool:
        """Set up Aider configuration - called by base class"""
        # Additional tool configuration can be added here if needed
        return True

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate Aider with available MCP servers if applicable"""
        if mcp_config["count"] == 0:
            self.status.log("No MCP servers to integrate")
            return True

        # Aider doesn't have native MCP support like Claude Code,
        # but we could potentially add custom integrations here
        self.status.log(
            f"Found {mcp_config['count']} MCP server(s) - no direct integration available"
        )
        return True
