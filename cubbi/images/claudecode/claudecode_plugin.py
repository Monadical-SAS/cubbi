#!/usr/bin/env python3
"""
Claude Code Plugin for Cubbi
Handles authentication setup and configuration for Claude Code
"""

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

from cubbi_init import ToolPlugin

# API key mappings from environment variables to Claude Code configuration
API_KEY_MAPPINGS = {
    "ANTHROPIC_API_KEY": "api_key",
    "ANTHROPIC_AUTH_TOKEN": "auth_token",
    "ANTHROPIC_CUSTOM_HEADERS": "custom_headers",
}

# Enterprise integration environment variables
ENTERPRISE_MAPPINGS = {
    "CLAUDE_CODE_USE_BEDROCK": "use_bedrock",
    "CLAUDE_CODE_USE_VERTEX": "use_vertex",
    "HTTP_PROXY": "http_proxy",
    "HTTPS_PROXY": "https_proxy",
    "DISABLE_TELEMETRY": "disable_telemetry",
}


class ClaudeCodePlugin(ToolPlugin):
    """Plugin for setting up Claude Code authentication and configuration"""
    
    @property
    def tool_name(self) -> str:
        return "claudecode"

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

    def _get_claude_dir(self) -> Path:
        """Get the Claude Code configuration directory"""
        return Path("/home/cubbi/.claude")

    def _ensure_claude_dir(self) -> Path:
        """Ensure Claude directory exists with correct ownership"""
        claude_dir = self._get_claude_dir()
        
        try:
            claude_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._set_ownership(claude_dir)
        except OSError as e:
            self.status.log(f"Failed to create Claude directory {claude_dir}: {e}", "ERROR")
            
        return claude_dir
        
    def initialize(self) -> bool:
        """Initialize Claude Code configuration"""
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
            self.status.log("   Please set ANTHROPIC_API_KEY environment variable", "WARNING")
            self.status.log("   Claude Code will run without authentication", "INFO")
            # Return True to allow container to start without API key
            # Users can still use Claude Code with their own authentication methods
            return True
    
    def _create_settings(self) -> Optional[Dict]:
        """Create Claude Code settings configuration"""
        settings = {}
        
        # Core authentication
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
            
        # Basic authentication setup
        settings["apiKey"] = api_key
        
        # Custom authorization token (optional)
        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if auth_token:
            settings["authToken"] = auth_token
            
        # Custom headers (optional)
        custom_headers = os.environ.get("ANTHROPIC_CUSTOM_HEADERS")
        if custom_headers:
            try:
                # Expect JSON string format
                settings["customHeaders"] = json.loads(custom_headers)
            except json.JSONDecodeError:
                self.status.log("⚠️ Invalid ANTHROPIC_CUSTOM_HEADERS format, skipping", "WARNING")
        
        # Enterprise integration settings
        if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "true":
            settings["provider"] = "bedrock"
            
        if os.environ.get("CLAUDE_CODE_USE_VERTEX") == "true":
            settings["provider"] = "vertex"
            
        # Network proxy settings
        http_proxy = os.environ.get("HTTP_PROXY")
        https_proxy = os.environ.get("HTTPS_PROXY")
        if http_proxy or https_proxy:
            settings["proxy"] = {}
            if http_proxy:
                settings["proxy"]["http"] = http_proxy
            if https_proxy:
                settings["proxy"]["https"] = https_proxy
                
        # Telemetry settings
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
                "websearch": {"allowed": True}
            }
        }
        
        return settings
    
    def _write_settings(self, settings_file: Path, settings: Dict) -> bool:
        """Write settings to Claude Code configuration file"""
        try:
            # Write settings with secure permissions
            with open(settings_file, 'w') as f:
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
        """Set up Claude Code configuration - called by base class"""
        # Additional tool configuration can be added here if needed
        return True

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate Claude Code with available MCP servers"""
        if mcp_config["count"] == 0:
            self.status.log("No MCP servers to integrate")
            return True

        # Claude Code has built-in MCP support, so we can potentially
        # configure MCP servers in the settings if needed
        self.status.log("MCP server integration available for Claude Code")
        return True