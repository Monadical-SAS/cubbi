#!/bin/bash
# Entrypoint script for Aider driver

# Run the standard initialization script
/mc-init.sh

# Start SSH server in the background
/usr/sbin/sshd

# Print welcome message
echo "==============================================="
echo "Aider driver container started"
echo "SSH server running on port 22"
echo "==============================================="
echo "To use aider, simply run 'aider' in the terminal."
echo "You can specify a directory or files to edit:"
echo "  aider your_code_directory/"
echo "  aider file1.py file2.py"
echo "==============================================="

# Keep container running
exec tail -f /dev/null