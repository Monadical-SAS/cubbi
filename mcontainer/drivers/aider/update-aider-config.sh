#!/bin/bash
# Script to update aider configuration with available MCP servers

# Path to aider config
AIDER_CONFIG="/root/.config/aider/config.yml"

# Ensure config file exists
if [ ! -f "$AIDER_CONFIG" ]; then
    mkdir -p "$(dirname "$AIDER_CONFIG")"
    touch "$AIDER_CONFIG"
fi

# Check if MCP_SERVERS environment variable is set
if [ -z "$MCP_SERVERS" ]; then
    echo "No MCP servers specified, using OpenAI API directly"
    exit 0
fi

# Parse MCP servers list
IFS=',' read -ra SERVERS <<< "$MCP_SERVERS"

# If no servers available, exit
if [ ${#SERVERS[@]} -eq 0 ]; then
    echo "No MCP servers available"
    exit 0
fi

# Use the first available server for now
# In the future, we may add load balancing or fallback logic
SERVER="${SERVERS[0]}"

echo "Configuring aider to use MCP server: $SERVER"

# Extract protocol, host, port and any path
if [[ "$SERVER" =~ ^(http|https)://([^:/]+)(:([0-9]+))?(/.*)?$ ]]; then
    PROTOCOL="${BASH_REMATCH[1]}"
    HOST="${BASH_REMATCH[2]}"
    PORT="${BASH_REMATCH[4]}"
    PATH_PREFIX="${BASH_REMATCH[5]:-/}"

    # Use default port based on protocol if not specified
    if [ -z "$PORT" ]; then
        if [ "$PROTOCOL" = "https" ]; then
            PORT=443
        else
            PORT=80
        fi
    fi

    # Construct the base URL for OpenAI API
    # Ensure PATH_PREFIX ends with a slash
    if [[ "$PATH_PREFIX" != */ ]]; then
        PATH_PREFIX="${PATH_PREFIX}/"
    fi

    API_BASE="${PROTOCOL}://${HOST}:${PORT}${PATH_PREFIX}"
    
    # Update aider config with the MCP server URL
    # First, remove any existing openai_api_base entry
    sed -i '/openai_api_base:/d' "$AIDER_CONFIG"
    
    # Then add the new one
    echo "openai_api_base: $API_BASE" >> "$AIDER_CONFIG"
    
    echo "Aider configured to use MCP server at $API_BASE"
else
    echo "Invalid MCP server URL: $SERVER"
fi