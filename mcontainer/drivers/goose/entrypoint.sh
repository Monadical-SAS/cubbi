#!/bin/bash
# Entrypoint script for Goose driver
# Executes the standard initialization script, which handles user setup,
# service startup (like sshd), and switching to the non-root user
# before running the container's command (CMD).

exec /mc-init.sh "$@"
