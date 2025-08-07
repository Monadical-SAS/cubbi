#!/usr/bin/env python3

import json
import os
import stat
from pathlib import Path
from typing import Dict, Optional

from cubbi_init import ToolPlugin, cubbi_config


class ClaudeCodePlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "claudecode"

    def _get_user_ids(self) -> tuple[int, int]:
        return cubbi_config.user.uid, cubbi_config.user.gid

    def _set_ownership(self, path: Path) -> None:
        user_id, group_id = self._get_user_ids()
        try:
            os.chown(path, user_id, group_id)
        except OSError as e:
            self.status.log(f"Failed to set ownership for {path}: {e}", "WARNING")

    def _get_claude_dir(self) -> Path:
        return Path("/home/cubbi/.claude")

    def _ensure_claude_dir(self) -> Path:
        claude_dir = self._get_claude_dir()

        try:
            claude_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._set_ownership(claude_dir)
        except OSError as e:
            self.status.log(
                f"Failed to create Claude directory {claude_dir}: {e}", "ERROR"
            )

        return claude_dir

    def initialize(self) -> bool:
        self.status.log("Setting up Claude Code authentication...")

        # Ensure Claude directory exists
        claude_dir = self._ensure_claude_dir()

        # Create settings configuration
        settings = self._create_settings()

        if settings:
            settings_file = claude_dir / "settings.json"
            success = self._write_settings(settings_file, settings)
            if success:
                self.status.log("✅ Claude Code authentication configured successfully")
                return True
            else:
                return False
        else:
            self.status.log("⚠️ No authentication configuration found", "WARNING")
            self.status.log(
                "   Please set ANTHROPIC_API_KEY environment variable", "WARNING"
            )
            self.status.log("   Claude Code will run without authentication", "INFO")
            # Return True to allow container to start without API key
            # Users can still use Claude Code with their own authentication methods
            return True

    def _create_settings(self) -> Optional[Dict]:
        settings = {}

        # Get Anthropic provider configuration from cubbi_config
        anthropic_provider = None
        for provider_name, provider_config in cubbi_config.providers.items():
            if provider_config.type == "anthropic":
                anthropic_provider = provider_config
                break

        if not anthropic_provider or not anthropic_provider.api_key:
            # Fallback to environment variable for backward compatibility
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return None
            settings["apiKey"] = api_key
        else:
            settings["apiKey"] = anthropic_provider.api_key

        # Custom authorization token (optional) - still from environment
        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if auth_token:
            settings["authToken"] = auth_token

        # Custom headers (optional) - still from environment
        custom_headers = os.environ.get("ANTHROPIC_CUSTOM_HEADERS")
        if custom_headers:
            try:
                # Expect JSON string format
                settings["customHeaders"] = json.loads(custom_headers)
            except json.JSONDecodeError:
                self.status.log(
                    "⚠️ Invalid ANTHROPIC_CUSTOM_HEADERS format, skipping", "WARNING"
                )

        # Enterprise integration settings - still from environment
        if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "true":
            settings["provider"] = "bedrock"

        if os.environ.get("CLAUDE_CODE_USE_VERTEX") == "true":
            settings["provider"] = "vertex"

        # Network proxy settings - still from environment
        http_proxy = os.environ.get("HTTP_PROXY")
        https_proxy = os.environ.get("HTTPS_PROXY")
        if http_proxy or https_proxy:
            settings["proxy"] = {}
            if http_proxy:
                settings["proxy"]["http"] = http_proxy
            if https_proxy:
                settings["proxy"]["https"] = https_proxy

        # Telemetry settings - still from environment
        if os.environ.get("DISABLE_TELEMETRY") == "true":
            settings["telemetry"] = {"enabled": False}

        # Tool permissions (allow all by default in Cubbi environment)
        settings["permissions"] = {
            "tools": {
                "read": {"allowed": True},
                "write": {"allowed": True},
                "edit": {"allowed": True},
                "bash": {"allowed": True},
                "webfetch": {"allowed": True},
                "websearch": {"allowed": True},
            }
        }

        return settings

    def _write_settings(self, settings_file: Path, settings: Dict) -> bool:
        try:
            # Write settings with secure permissions
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)

            # Set ownership and secure file permissions (read/write for owner only)
            self._set_ownership(settings_file)
            os.chmod(settings_file, stat.S_IRUSR | stat.S_IWUSR)

            self.status.log(f"Created Claude Code settings at {settings_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Claude Code settings: {e}", "ERROR")
            return False

    def setup_tool_configuration(self) -> bool:
        # Additional tool configuration can be added here if needed
        return True

    def integrate_mcp_servers(self) -> bool:
        if not cubbi_config.mcps:
            self.status.log("No MCP servers to integrate")
            return True

        # Claude Code has built-in MCP support, so we can potentially
        # configure MCP servers in the settings if needed
        self.status.log("MCP server integration available for Claude Code")
        return True
