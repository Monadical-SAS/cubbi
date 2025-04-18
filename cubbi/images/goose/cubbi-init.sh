#!/bin/bash
# Standardized initialization script for Cubbi images

# Redirect all output to both stdout and the log file
exec > >(tee -a /init.log) 2>&1

# Mark initialization as started
echo "=== Cubbi Initialization started at $(date) ==="

# --- START INSERTED BLOCK ---

# Default UID/GID if not provided (should be passed by cubbi tool)
CUBBI_USER_ID=${CUBBI_USER_ID:-1000}
CUBBI_GROUP_ID=${CUBBI_GROUP_ID:-1000}

echo "Using UID: $CUBBI_USER_ID, GID: $CUBBI_GROUP_ID"

# Create group if it doesn't exist
if ! getent group cubbi > /dev/null; then
    groupadd -g $CUBBI_GROUP_ID cubbi
else
    # If group exists but has different GID, modify it
    EXISTING_GID=$(getent group cubbi | cut -d: -f3)
    if [ "$EXISTING_GID" != "$CUBBI_GROUP_ID" ]; then
        groupmod -g $CUBBI_GROUP_ID cubbi
    fi
fi

# Create user if it doesn't exist
if ! getent passwd cubbi > /dev/null; then
    useradd --shell /bin/bash --uid $CUBBI_USER_ID --gid $CUBBI_GROUP_ID --no-create-home cubbi
else
    # If user exists but has different UID/GID, modify it
    EXISTING_UID=$(getent passwd cubbi | cut -d: -f3)
    EXISTING_GID=$(getent passwd cubbi | cut -d: -f4)
    if [ "$EXISTING_UID" != "$CUBBI_USER_ID" ] || [ "$EXISTING_GID" != "$CUBBI_GROUP_ID" ]; then
        usermod --uid $CUBBI_USER_ID --gid $CUBBI_GROUP_ID cubbi
    fi
fi

# Create home directory and set permissions
mkdir -p /home/cubbi
chown $CUBBI_USER_ID:$CUBBI_GROUP_ID /home/cubbi
mkdir -p /app
chown $CUBBI_USER_ID:$CUBBI_GROUP_ID /app

# Copy /root/.local/bin to the user's home directory
if [ -d /root/.local/bin ]; then
    echo "Copying /root/.local/bin to /home/cubbi/.local/bin..."
    mkdir -p /home/cubbi/.local/bin
    cp -r /root/.local/bin/* /home/cubbi/.local/bin/
    chown -R $CUBBI_USER_ID:$CUBBI_GROUP_ID /home/cubbi/.local
fi

# Start SSH server only if explicitly enabled
if [ "$CUBBI_SSH_ENABLED" = "true" ]; then
  echo "Starting SSH server..."
  /usr/sbin/sshd
else
  echo "SSH server disabled (use --ssh flag to enable)"
fi

# --- END INSERTED BLOCK ---

echo "INIT_COMPLETE=false" > /init.status

# Project initialization
if [ -n "$CUBBI_PROJECT_URL" ]; then
    echo "Initializing project: $CUBBI_PROJECT_URL"

    # Set up SSH key if provided
    if [ -n "$CUBBI_GIT_SSH_KEY" ]; then
        mkdir -p ~/.ssh
        echo "$CUBBI_GIT_SSH_KEY" > ~/.ssh/id_ed25519
        chmod 600 ~/.ssh/id_ed25519
        ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
        ssh-keyscan gitlab.com >> ~/.ssh/known_hosts 2>/dev/null
        ssh-keyscan bitbucket.org >> ~/.ssh/known_hosts 2>/dev/null
    fi

    # Set up token if provided
    if [ -n "$CUBBI_GIT_TOKEN" ]; then
        git config --global credential.helper store
        echo "https://$CUBBI_GIT_TOKEN:x-oauth-basic@github.com" > ~/.git-credentials
    fi

    # Clone repository
    git clone $CUBBI_PROJECT_URL /app
    cd /app

    # Run project-specific initialization if present
    if [ -f "/app/.cubbi/init.sh" ]; then
        bash /app/.cubbi/init.sh
    fi

    # Persistent configs are now directly mounted as volumes
    # No need to create symlinks anymore
    if [ -n "$CUBBI_CONFIG_DIR" ] && [ -d "$CUBBI_CONFIG_DIR" ]; then
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

# Ensure /cubbi-config directory exists (required for symlinks)
if [ ! -d "/cubbi-config" ]; then
    echo "Creating /cubbi-config directory since it doesn't exist"
    mkdir -p /cubbi-config
    chown $CUBBI_USER_ID:$CUBBI_GROUP_ID /cubbi-config
fi

# Create symlinks for persistent configurations defined in the image
if [ -n "$CUBBI_PERSISTENT_LINKS" ]; then
    echo "Creating persistent configuration symlinks..."
    # Split by semicolon
    IFS=';' read -ra LINKS <<< "$CUBBI_PERSISTENT_LINKS"
    for link_pair in "${LINKS[@]}"; do
        # Split by colon
        IFS=':' read -r source_path target_path <<< "$link_pair"

        if [ -z "$source_path" ] || [ -z "$target_path" ]; then
            echo "Warning: Invalid link pair format '$link_pair', skipping."
            continue
        fi

        echo "Processing link: $source_path -> $target_path"
        parent_dir=$(dirname "$source_path")

        # Ensure parent directory of the link source exists and is owned by cubbi
        if [ ! -d "$parent_dir" ]; then
             echo "Creating parent directory: $parent_dir"
             mkdir -p "$parent_dir"
             echo "Changing ownership of parent $parent_dir to $CUBBI_USER_ID:$CUBBI_GROUP_ID"
             chown "$CUBBI_USER_ID:$CUBBI_GROUP_ID" "$parent_dir" || echo "Warning: Could not chown parent $parent_dir"
        fi

        # Create the symlink (force, no-dereference)
        echo "Creating symlink: ln -sfn $target_path $source_path"
        ln -sfn "$target_path" "$source_path"
        # Optionally, change ownership of the symlink itself
        echo "Changing ownership of symlink $source_path to $CUBBI_USER_ID:$CUBBI_GROUP_ID"
        chown -h "$CUBBI_USER_ID:$CUBBI_GROUP_ID" "$source_path" || echo "Warning: Could not chown symlink $source_path"

    done
    echo "Persistent configuration symlinks created."
fi

# Update Goose configuration with available MCP servers (run as cubbi after symlinks are created)
if [ -f "/usr/local/bin/update-goose-config.py" ]; then
    echo "Updating Goose configuration with MCP servers as cubbi..."
    gosu cubbi /usr/local/bin/update-goose-config.py
elif [ -f "$(dirname "$0")/update-goose-config.py" ]; then
    echo "Updating Goose configuration with MCP servers as cubbi..."
    gosu cubbi "$(dirname "$0")/update-goose-config.py"
else
    echo "Warning: update-goose-config.py script not found. Goose configuration will not be updated."
fi

# Run the user command first, if set, as cubbi
if [ -n "$CUBBI_RUN_COMMAND" ]; then
    echo "--- Executing initial command: $CUBBI_RUN_COMMAND ---";
    gosu cubbi sh -c "$CUBBI_RUN_COMMAND"; # Run user command as cubbi
    COMMAND_EXIT_CODE=$?;
    echo "--- Initial command finished (exit code: $COMMAND_EXIT_CODE) ---";
fi;

# Mark initialization as complete
echo "=== Cubbi Initialization completed at $(date) ==="
echo "INIT_COMPLETE=true" > /init.status

exec gosu cubbi "$@"
