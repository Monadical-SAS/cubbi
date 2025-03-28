#!/bin/bash
# Standardized initialization script for MC drivers

# Redirect all output to both stdout and the log file
exec > >(tee -a /init.log) 2>&1

# Mark initialization as started
echo "=== MC Initialization started at $(date) ==="
echo "INIT_COMPLETE=false" > /init.status

# Ensure API key is available
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY environment variable is required for aider."
    echo "INIT_COMPLETE=false" > /init.status
    echo "INIT_ERROR=Missing OPENAI_API_KEY" >> /init.status
    # Continue anyway to allow troubleshooting
fi

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

    # Configure git for aider
    git config --global user.email "aider@example.com"
    git config --global user.name "Aider AI Assistant"

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

# Set up Aider configuration
mkdir -p /app/.aider
mkdir -p /root/.config/aider

# Configure Aider
cat > /root/.config/aider/config.yml <<EOL
model: ${OPENAI_MODEL:-gpt-4}
show_diffs: true
auto_commits: true
send_git_metadata: true
edit_format: vertical
EOL

# If custom OpenAI API base is provided
if [ -n "$OPENAI_API_BASE" ]; then
    echo "openai_api_base: $OPENAI_API_BASE" >> /root/.config/aider/config.yml
fi

# Set up aider editor preference
if [ -n "$AIDER_EDITOR" ]; then
    echo "editor: $AIDER_EDITOR" >> /root/.config/aider/config.yml
fi

# Update Aider configuration with available MCP servers
if [ -f "/usr/local/bin/update-aider-config.sh" ]; then
    echo "Updating Aider configuration with MCP servers..."
    bash /usr/local/bin/update-aider-config.sh
fi

echo "MC driver initialization complete"

# Mark initialization as complete
echo "=== MC Initialization completed at $(date) ==="
echo "INIT_COMPLETE=true" > /init.status