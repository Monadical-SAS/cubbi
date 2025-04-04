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

# Create home directory and set permissions
mkdir -p /home/mcuser
chown $MC_USER_ID:$MC_GROUP_ID /home/mcuser
mkdir -p /app
chown $MC_USER_ID:$MC_GROUP_ID /app

# Copy /root/.local/bin to the user's home directory
if [ -d /root/.local/bin ]; then
    echo "Copying /root/.local/bin to /home/mcuser/.local/bin..."
    mkdir -p /home/mcuser/.local/bin
    cp -r /root/.local/bin/* /home/mcuser/.local/bin/
    chown -R $MC_USER_ID:$MC_GROUP_ID /home/mcuser/.local
fi

# Start SSH server only if explicitly enabled
if [ "$MC_SSH_ENABLED" = "true" ]; then
  echo "Starting SSH server..."
  /usr/sbin/sshd
else
  echo "SSH server disabled (use --ssh flag to enable)"
fi

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

# Ensure /mc-config directory exists (required for symlinks)
if [ ! -d "/mc-config" ]; then
    echo "Creating /mc-config directory since it doesn't exist"
    mkdir -p /mc-config
    chown $MC_USER_ID:$MC_GROUP_ID /mc-config
fi

# Create symlinks for persistent configurations defined in the driver
if [ -n "$MC_PERSISTENT_LINKS" ]; then
    echo "Creating persistent configuration symlinks..."
    # Split by semicolon
    IFS=';' read -ra LINKS <<< "$MC_PERSISTENT_LINKS"
    for link_pair in "${LINKS[@]}"; do
        # Split by colon
        IFS=':' read -r source_path target_path <<< "$link_pair"

        if [ -z "$source_path" ] || [ -z "$target_path" ]; then
            echo "Warning: Invalid link pair format '$link_pair', skipping."
            continue
        fi

        echo "Processing link: $source_path -> $target_path"
        parent_dir=$(dirname "$source_path")

        # Ensure parent directory of the link source exists and is owned by mcuser
        if [ ! -d "$parent_dir" ]; then
             echo "Creating parent directory: $parent_dir"
             mkdir -p "$parent_dir"
             echo "Changing ownership of parent $parent_dir to $MC_USER_ID:$MC_GROUP_ID"
             chown "$MC_USER_ID:$MC_GROUP_ID" "$parent_dir" || echo "Warning: Could not chown parent $parent_dir"
        fi

        # Create the symlink (force, no-dereference)
        echo "Creating symlink: ln -sfn $target_path $source_path"
        ln -sfn "$target_path" "$source_path"

        # Optionally, change ownership of the symlink itself
        echo "Changing ownership of symlink $source_path to $MC_USER_ID:$MC_GROUP_ID"
        chown -h "$MC_USER_ID:$MC_GROUP_ID" "$source_path" || echo "Warning: Could not chown symlink $source_path"

    done
    echo "Persistent configuration symlinks created."
fi

# Update Goose configuration with available MCP servers (run as mcuser after symlinks are created)
if [ -f "/usr/local/bin/update-goose-config.py" ]; then
    echo "Updating Goose configuration with MCP servers as mcuser..."
    gosu mcuser /usr/local/bin/update-goose-config.py
elif [ -f "$(dirname "$0")/update-goose-config.py" ]; then
    echo "Updating Goose configuration with MCP servers as mcuser..."
    gosu mcuser "$(dirname "$0")/update-goose-config.py"
else
    echo "Warning: update-goose-config.py script not found. Goose configuration will not be updated."
fi

# Run the user command first, if set, as mcuser
if [ -n "$MC_RUN_COMMAND" ]; then
    echo "--- Executing initial command: $MC_RUN_COMMAND ---";
    gosu mcuser sh -c "$MC_RUN_COMMAND"; # Run user command as mcuser
    COMMAND_EXIT_CODE=$?;
    echo "--- Initial command finished (exit code: $COMMAND_EXIT_CODE) ---";
fi;

# Mark initialization as complete
echo "=== MC Initialization completed at $(date) ==="
echo "INIT_COMPLETE=true" > /init.status

exec gosu mcuser "$@"
