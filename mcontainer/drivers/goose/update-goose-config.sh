#!/bin/bash
# Script to update Goose configuration with MCP servers using Python standard library

# Define config path
GOOSE_CONFIG="$HOME/.config/goose/config.yaml"
CONFIG_DIR="$(dirname "$GOOSE_CONFIG")"

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Function to update config using Python without yaml module
update_config() {
    python3 - << 'EOF'
import os
import json
import re

# Path to goose config
config_path = os.path.expanduser('~/.config/goose/config.yaml')

# Check if file exists, create if not
if not os.path.exists(config_path):
    with open(config_path, 'w') as f:
        f.write("extensions:\n")

# Read the entire file
with open(config_path, 'r') as f:
    content = f.read()

# Get MCP information from environment variables
mcp_count = int(os.environ.get('MCP_COUNT', '0'))
mcp_names_str = os.environ.get('MCP_NAMES', '[]')

try:
    mcp_names = json.loads(mcp_names_str)
    print(f"Found {mcp_count} MCP servers: {', '.join(mcp_names)}")
except:
    mcp_names = []
    print("Error parsing MCP_NAMES environment variable")

# Check if extensions key exists, add if not
if 'extensions:' not in content:
    content = "extensions:\n" + content

# Process each MCP - we'll collect the mcp configs to add or update
mcp_configs = []
for idx in range(mcp_count):
    mcp_name = os.environ.get(f'MCP_{idx}_NAME')
    mcp_type = os.environ.get(f'MCP_{idx}_TYPE')
    mcp_host = os.environ.get(f'MCP_{idx}_HOST')
    
    # Always use container's SSE port (8080) not the host-bound port
    if mcp_name and mcp_host:
        # Use standard MCP SSE port (8080)
        mcp_url = f"http://{mcp_host}:8080/sse"
        print(f"Processing MCP extension: {mcp_name} ({mcp_type}) - {mcp_url}")
        mcp_configs.append((mcp_name, mcp_url))
    elif mcp_name and os.environ.get(f'MCP_{idx}_URL'):
        # For remote MCPs, use the URL provided in environment
        mcp_url = os.environ.get(f'MCP_{idx}_URL')
        print(f"Processing remote MCP extension: {mcp_name} ({mcp_type}) - {mcp_url}")
        mcp_configs.append((mcp_name, mcp_url))

# Now we'll update the config file line by line, preserving all content
lines = content.split('\n')
output_lines = []
in_extensions = False
current_ext = None
extension_added = set()  # Track which extensions we've processed

# First pass - update existing extensions and track them
for line in lines:
    # Check if we're entering extensions section
    if line.strip() == 'extensions:':
        in_extensions = True
        output_lines.append(line)
        continue

    # Look for extension definition (2-space indentation)
    if in_extensions and re.match(r'^  (\w+):', line):
        match = re.match(r'^  (\w+):', line)
        current_ext = match.group(1)
        output_lines.append(line)
        
        # Mark as seen if this is one of our MCPs
        for mcp_name, _ in mcp_configs:
            if mcp_name == current_ext:
                extension_added.add(mcp_name)
        continue
    
    # If we're in an MCP extension that we need to update
    if in_extensions and current_ext and current_ext in [n for n, _ in mcp_configs]:
        # If this is a URI line, replace it with our URL
        if line.strip().startswith('uri:'):
            for mcp_name, mcp_url in mcp_configs:
                if mcp_name == current_ext:
                    output_lines.append(f'    uri: {mcp_url}')
                    break
        # If this is a type line, ensure it's SSE
        elif line.strip().startswith('type:'):
            output_lines.append('    type: sse')
        # If this is enabled line, ensure it's true
        elif line.strip().startswith('enabled:'):
            output_lines.append('    enabled: true')
        # Otherwise keep the line
        else:
            output_lines.append(line)
        continue
    
    # If we're moving to a non-2-space indented line, we're out of the current extension
    if in_extensions and current_ext and not line.startswith('    ') and line.strip():
        current_ext = None
    
    # For any other line, just add it
    output_lines.append(line)

# Add any MCP extensions that weren't found in the existing config
if in_extensions:
    for mcp_name, mcp_url in mcp_configs:
        if mcp_name not in extension_added:
            print(f"Adding new MCP extension: {mcp_name}")
            output_lines.append(f'  {mcp_name}:')
            output_lines.append(f'    enabled: true')
            output_lines.append(f'    name: {mcp_name}')
            output_lines.append(f'    timeout: 60')
            output_lines.append(f'    type: sse')
            output_lines.append(f'    uri: {mcp_url}')
            output_lines.append(f'    envs: {{}}')

# Write the updated content back
with open(config_path, 'w') as f:
    f.write('\n'.join(output_lines))

print(f"Updated Goose configuration at {config_path}")
EOF
}

# Check if MCP servers are defined
if [ -n "$MCP_COUNT" ] && [ "$MCP_COUNT" -gt 0 ]; then
    echo "Updating Goose configuration with MCP servers..."
    update_config
    echo "Goose configuration updated successfully!"
else
    echo "No MCP servers found, using default Goose configuration."
fi