#!/usr/bin/env python3

import json
import os
import stat
from pathlib import Path

from cubbi_init import ToolPlugin, cubbi_config, set_ownership


class ClaudeCodePlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "claudecode"

    def _get_claude_dir(self) -> Path:
        return Path("/home/cubbi/.claude")

    def is_already_configured(self) -> bool:
        settings_file = self._get_claude_dir() / "settings.json"
        return settings_file.exists()

    def configure(self) -> bool:
        self.status.log("Setting up Claude Code authentication...")

        claude_dir = self.create_directory_with_ownership(self._get_claude_dir())
        claude_dir.chmod(0o700)

        settings = self._create_settings()

        if settings:
            settings_file = claude_dir / "settings.json"
            success = self._write_settings(settings_file, settings)
            if success:
                self.status.log("✅ Claude Code authentication configured successfully")
                self._integrate_mcp_servers()
                return True
            else:
                return False
        else:
            self.status.log("⚠️ No authentication configuration found", "WARNING")
            self.status.log(
                "   Please set ANTHROPIC_API_KEY environment variable", "WARNING"
            )
            self.status.log("   Claude Code will run without authentication", "INFO")
            self._integrate_mcp_servers()
            return True

    def _integrate_mcp_servers(self) -> None:
        if not cubbi_config.mcps:
            self.status.log("No MCP servers to integrate")
            return

        self.status.log("MCP server integration available for Claude Code")

    def _create_settings(self) -> dict | None:
        settings = {}

        anthropic_provider = None
        for provider_name, provider_config in cubbi_config.providers.items():
            if provider_config.type == "anthropic":
                anthropic_provider = provider_config
                break

        if not anthropic_provider or not anthropic_provider.api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return None
            settings["apiKey"] = api_key
        else:
            settings["apiKey"] = anthropic_provider.api_key

        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if auth_token:
            settings["authToken"] = auth_token

        custom_headers = os.environ.get("ANTHROPIC_CUSTOM_HEADERS")
        if custom_headers:
            try:
                settings["customHeaders"] = json.loads(custom_headers)
            except json.JSONDecodeError:
                self.status.log(
                    "⚠️ Invalid ANTHROPIC_CUSTOM_HEADERS format, skipping", "WARNING"
                )

        if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "true":
            settings["provider"] = "bedrock"

        if os.environ.get("CLAUDE_CODE_USE_VERTEX") == "true":
            settings["provider"] = "vertex"

        http_proxy = os.environ.get("HTTP_PROXY")
        https_proxy = os.environ.get("HTTPS_PROXY")
        if http_proxy or https_proxy:
            settings["proxy"] = {}
            if http_proxy:
                settings["proxy"]["http"] = http_proxy
            if https_proxy:
                settings["proxy"]["https"] = https_proxy

        if os.environ.get("DISABLE_TELEMETRY") == "true":
            settings["telemetry"] = {"enabled": False}

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

    def _write_settings(self, settings_file: Path, settings: dict) -> bool:
        try:
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)

            set_ownership(settings_file)
            os.chmod(settings_file, stat.S_IRUSR | stat.S_IWUSR)

            self.status.log(f"Created Claude Code settings at {settings_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Claude Code settings: {e}", "ERROR")
            return False


PLUGIN_CLASS = ClaudeCodePlugin
