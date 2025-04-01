#!/bin/bash
# Standardized initialization script for MC drivers

# Redirect all output to both stdout and the log file
exec > >(tee -a /init.log) 2>&1

# Mark initialization as started
echo "=== MC Initialization started at $(date) ==="

# --- START INSERTED BLOCK ---

# Default UID/GID if not provided (should be passed by mc tool)
MC_USER_ID=${MC_USER_ID:-1000}
MC_GROUP_ID=${MC_GROUP_ID:-1000}

echo "Using UID: $MC_USER_ID, GID: $MC_GROUP_ID"

# Create group if it doesn't exist
if ! getent group mcuser > /dev/null; then
    groupadd -g $MC_GROUP_ID mcuser
else
    # If group exists but has different GID, modify it
    EXISTING_GID=$(getent group mcuser | cut -d: -f3)
    if [ "$EXISTING_GID" != "$MC_GROUP_ID" ]; then
        groupmod -g $MC_GROUP_ID mcuser
    fi
fi

# Create user if it doesn't exist
if ! getent passwd mcuser > /dev/null; then
    useradd --shell /bin/bash --uid $MC_USER_ID --gid $MC_GROUP_ID --no-create-home mcuser
else
    # If user exists but has different UID/GID, modify it
    EXISTING_UID=$(getent passwd mcuser | cut -d: -f3)
    EXISTING_GID=$(getent passwd mcuser | cut -d: -f4)
    if [ "$EXISTING_UID" != "$MC_USER_ID" ] || [ "$EXISTING_GID" != "$MC_GROUP_ID" ]; then
        usermod --uid $MC_USER_ID --gid $MC_GROUP_ID mcuser
    fi
fi

# Create home directory and set permissions if it doesn't exist
if [ ! -d "/home/mcuser" ]; then
    mkdir -p /home/mcuser
    chown $MC_USER_ID:$MC_GROUP_ID /home/mcuser
fi
# Ensure /app exists and has correct ownership (important for volume mounts)
mkdir -p /app
chown $MC_USER_ID:$MC_GROUP_ID /app

# Start SSH server as root before switching user
echo "Starting SSH server..."
/usr/sbin/sshd

# --- END INSERTED BLOCK ---

echo "INIT_COMPLETE=false" > /init.status

# Project initialization
if [ -n "$MC_PROJECT_URL" ]; then
    echo "Initializing project: $MC_PROJECT_URL"

    # Set up SSH key if provided
    if [ -n "$MC_GIT_SSH_KEY" ]; then
        mkdir -p ~/.ssh
        echo "$MC_GIT_SSH_KEY" > ~/.ssh/id_ed25519
        chmod 600 ~/.ssh/id_ed25519
        ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
        ssh-keyscan gitlab.com >> ~/.ssh/known_hosts 2>/dev/null
        ssh-keyscan bitbucket.org >> ~/.ssh/known_hosts 2>/dev/null
    fi

    # Set up token if provided
    if [ -n "$MC_GIT_TOKEN" ]; then
        git config --global credential.helper store
        echo "https://$MC_GIT_TOKEN:x-oauth-basic@github.com" > ~/.git-credentials
    fi

    # Clone repository
    git clone $MC_PROJECT_URL /app
    cd /app

    # Run project-specific initialization if present
    if [ -f "/app/.mc/init.sh" ]; then
        bash /app/.mc/init.sh
    fi

    # Persistent configs are now directly mounted as volumes
    # No need to create symlinks anymore
    if [ -n "$MC_CONFIG_DIR" ] && [ -d "$MC_CONFIG_DIR" ]; then
        echo "Using persistent configuration volumes (direct mounts)"
    fi
fi

# Goose uses self-hosted instance, no API key required

# Set up Langfuse logging if credentials are provided
if [ -n "$LANGFUSE_INIT_PROJECT_SECRET_KEY" ] && [ -n "$LANGFUSE_INIT_PROJECT_PUBLIC_KEY" ]; then
    echo "Setting up Langfuse logging"
    export LANGFUSE_INIT_PROJECT_SECRET_KEY="$LANGFUSE_INIT_PROJECT_SECRET_KEY"
    export LANGFUSE_INIT_PROJECT_PUBLIC_KEY="$LANGFUSE_INIT_PROJECT_PUBLIC_KEY"
    export LANGFUSE_URL="${LANGFUSE_URL:-https://cloud.langfuse.com}"
fi

# Update Goose configuration with available MCP servers
if [ -f "/usr/local/bin/update-goose-config.sh" ]; then
    echo "Updating Goose configuration with MCP servers..."
    bash /usr/local/bin/update-goose-config.sh
elif [ -f "$(dirname "$0")/update-goose-config.sh" ]; then
    echo "Updating Goose configuration with MCP servers..."
    bash "$(dirname "$0")/update-goose-config.sh"
else
    echo "Warning: update-goose-config.sh script not found. Goose configuration will not be updated."
fi

echo "MC driver initialization complete"

# Mark initialization as complete
echo "=== MC Initialization completed at $(date) ==="
echo "INIT_COMPLETE=true" > /init.status

# Switch to the non-root user and execute the container's CMD
exec gosu mcuser "$@"
