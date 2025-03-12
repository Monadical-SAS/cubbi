#!/bin/bash
# Standardized initialization script for MC drivers

# Redirect all output to both stdout and the log file
exec > >(tee -a /init.log) 2>&1

# Mark initialization as started
echo "=== MC Initialization started at $(date) ==="
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

echo "MC driver initialization complete"

# Mark initialization as complete
echo "=== MC Initialization completed at $(date) ==="
echo "INIT_COMPLETE=true" > /init.status
