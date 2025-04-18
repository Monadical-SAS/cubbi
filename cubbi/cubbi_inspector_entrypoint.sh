#!/bin/sh
# This script modifies the Express server to bind to all interfaces

# Try to find the CLI script
CLI_FILE=$(find /app -name "cli.js" | grep -v node_modules | head -1)

if [ -z "$CLI_FILE" ]; then
  echo "Could not find CLI file. Trying common locations..."
  for path in "/app/client/bin/cli.js" "/app/bin/cli.js" "./client/bin/cli.js" "./bin/cli.js"; do
    if [ -f "$path" ]; then
      CLI_FILE="$path"
      break
    fi
  done
fi

if [ -z "$CLI_FILE" ]; then
  echo "ERROR: Could not find the MCP Inspector CLI file."
  exit 1
fi

echo "Found CLI file at: $CLI_FILE"

# Make a backup of the original file
cp "$CLI_FILE" "$CLI_FILE.bak"

# Modify the file to use 0.0.0.0 as the host
sed -i 's/app.listen(PORT/app.listen(PORT, "0.0.0.0"/g' "$CLI_FILE"
sed -i 's/server.listen(port/server.listen(port, "0.0.0.0"/g' "$CLI_FILE"
sed -i 's/listen(PORT/listen(PORT, "0.0.0.0"/g' "$CLI_FILE"

echo "Modified server to listen on all interfaces (0.0.0.0)"

# Start the MCP Inspector
echo "Starting MCP Inspector on all interfaces..."
exec npm start
