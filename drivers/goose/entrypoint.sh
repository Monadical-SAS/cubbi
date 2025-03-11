#!/bin/bash
# Entrypoint script for Goose driver

# Run the standard initialization script
/mai-init.sh

# Start SSH server in the background
/usr/sbin/sshd

# Print welcome message
echo "==============================================="
echo "Goose driver container started"
echo "SSH server running on port 22"
echo "==============================================="

# Keep container running
exec tail -f /dev/null