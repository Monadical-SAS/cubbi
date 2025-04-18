#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["ruamel.yaml"]
# ///
import json
import os
from pathlib import Path

from ruamel.yaml import YAML

# Path to goose config
GOOSE_CONFIG = Path.home() / ".config/goose/config.yaml"
CONFIG_DIR = GOOSE_CONFIG.parent

# Create config directory if it doesn't exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def update_config():
    """Update Goose configuration based on environment variables and config file"""

    yaml = YAML()

    # Load or initialize the YAML configuration
    if not GOOSE_CONFIG.exists():
        config_data = {"extensions": {}}
    else:
        with GOOSE_CONFIG.open("r") as f:
            config_data = yaml.load(f)
            if "extensions" not in config_data:
                config_data["extensions"] = {}

    # Add default developer extension
    config_data["extensions"]["developer"] = {
        "enabled": True,
        "name": "developer",
        "timeout": 300,
        "type": "builtin",
    }

    # Update goose configuration with model and provider from environment variables
    goose_model = os.environ.get("CUBBI_MODEL")
    goose_provider = os.environ.get("CUBBI_PROVIDER")

    if goose_model:
        config_data["GOOSE_MODEL"] = goose_model
        print(f"Set GOOSE_MODEL to {goose_model}")

    if goose_provider:
        config_data["GOOSE_PROVIDER"] = goose_provider
        print(f"Set GOOSE_PROVIDER to {goose_provider}")

    # Get MCP information from environment variables
    mcp_count = int(os.environ.get("MCP_COUNT", "0"))
    mcp_names_str = os.environ.get("MCP_NAMES", "[]")

    try:
        mcp_names = json.loads(mcp_names_str)
        print(f"Found {mcp_count} MCP servers: {', '.join(mcp_names)}")
    except json.JSONDecodeError:
        mcp_names = []
        print("Error parsing MCP_NAMES environment variable")

    # Process each MCP - collect the MCP configs to add or update
    for idx in range(mcp_count):
        mcp_name = os.environ.get(f"MCP_{idx}_NAME")
        mcp_type = os.environ.get(f"MCP_{idx}_TYPE")
        mcp_host = os.environ.get(f"MCP_{idx}_HOST")

        # Always use container's SSE port (8080) not the host-bound port
        if mcp_name and mcp_host:
            # Use standard MCP SSE port (8080)
            mcp_url = f"http://{mcp_host}:8080/sse"
            print(f"Processing MCP extension: {mcp_name} ({mcp_type}) - {mcp_url}")
            config_data["extensions"][mcp_name] = {
                "enabled": True,
                "name": mcp_name,
                "timeout": 60,
                "type": "sse",
                "uri": mcp_url,
                "envs": {},
            }
        elif mcp_name and os.environ.get(f"MCP_{idx}_URL"):
            # For remote MCPs, use the URL provided in environment
            mcp_url = os.environ.get(f"MCP_{idx}_URL")
            print(
                f"Processing remote MCP extension: {mcp_name} ({mcp_type}) - {mcp_url}"
            )
            config_data["extensions"][mcp_name] = {
                "enabled": True,
                "name": mcp_name,
                "timeout": 60,
                "type": "sse",
                "uri": mcp_url,
                "envs": {},
            }

    # Write the updated configuration back to the file
    with GOOSE_CONFIG.open("w") as f:
        yaml.dump(config_data, f)

    print(f"Updated Goose configuration at {GOOSE_CONFIG}")


if __name__ == "__main__":
    update_config()
