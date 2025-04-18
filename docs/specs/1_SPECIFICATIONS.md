# Cubbi - Container Tool

## Overview

Cubbi is a command-line tool for managing ephemeral
containers that run AI tools and development environments. It works with both
local Docker and a dedicated remote web service that manages containers in a
Docker-in-Docker (DinD) environment.

## Technology Stack

### Cubbi Service
- **Web Framework**: FastAPI for high-performance, async API endpoints
- **Package Management**: uv (Astral) for dependency management
- **Database**: SQLite for development, PostgreSQL for production
- **Container Management**: Docker SDK for Python
- **Authentication**: OAuth 2.0 integration with Authentik

### Cubbi CLI
- **Language**: Python
- **Package Management**: uv for dependency management
- **Distribution**: Standalone binary via PyInstaller or similar
- **Configuration**: YAML for configuration files

## System Architecture

### Components

1. **CLI Tool (`cubbi`)**: The command-line interface users interact with
2. **Cubbi Service**: A web service that handles remote container execution
3. **Container Images**: Predefined container templates for various AI tools

### Architecture Diagram

```
┌─────────────┐           ┌─────────────────────────┐
│             │           │                         │
│  Cubbi CLI  │◄─────────►│  Local Docker Daemon    │
│  (cubbi)    │           │                         │
│             │           └─────────────────────────┘
└──────┬──────┘
       │
       │ REST API
       │
┌──────▼──────┐           ┌─────────────────────────┐
│             │           │                         │
│ Cubbi       │◄─────────►│  Docker-in-Docker       │
│ Service     │           │                         │
│             │           └─────────────────────────┘
└─────────────┘
       │
       ├──────────────┬───────────────┐
       │              │               │
┌──────▼──────┐ ┌─────▼─────┐  ┌──────▼──────┐
│             │ │           │  │             │
│  Fluentd    │ │ Langfuse  │  │ Other       │
│  Logging    │ │ Logging   │  │ Services    │
│             │ │           │  │             │
└─────────────┘ └───────────┘  └─────────────┘
```

## Core Concepts

- **Session**: An active container instance with a specific image
- **Image**: A predefined container template with specific AI tools installed
- **Remote**: A configured cubbi service instance

## User Configuration

Cubbi supports user-specific configuration via a YAML file located at `~/.config/cubbi/config.yaml`. This provides a way to set default values, store service credentials, and customize behavior without modifying code.

### Configuration File Structure

```yaml
# ~/.config/cubbi/config.yaml
defaults:
  image: "goose"  # Default image to use
  connect: true    # Automatically connect after creating session
  mount_local: true  # Mount local directory by default
  networks: []  # Default networks to connect to (besides cubbi-network)

services:
  # Service credentials with simplified naming
  # These are mapped to environment variables in containers
  langfuse:
    url: ""  # Will be set by the user
    public_key: "pk-lf-..."
    secret_key: "sk-lf-..."

  openai:
    api_key: "sk-..."

  anthropic:
    api_key: "sk-ant-..."

  openrouter:
    api_key: "sk-or-..."

docker:
  network: "cubbi-network"  # Default Docker network to use
  socket: "/var/run/docker.sock"  # Docker socket path

remote:
  default: "production"  # Default remote to use
  endpoints:
    production:
      url: "https://cubbi.monadical.com"
      auth_method: "oauth"
    staging:
      url: "https://cubbi-staging.monadical.com"
      auth_method: "oauth"

ui:
  colors: true  # Enable/disable colors in terminal output
  verbose: false  # Enable/disable verbose output
  table_format: "grid"  # Table format for session listings
```

### Environment Variable Mapping

The simplified configuration names are mapped to environment variables:

| Config Path | Environment Variable |
|-------------|---------------------|
| `services.langfuse.url` | `LANGFUSE_URL` |
| `services.langfuse.public_key` | `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` |
| `services.langfuse.secret_key` | `LANGFUSE_INIT_PROJECT_SECRET_KEY` |
| `services.openai.api_key` | `OPENAI_API_KEY` |
| `services.anthropic.api_key` | `ANTHROPIC_API_KEY` |
| `services.openrouter.api_key` | `OPENROUTER_API_KEY` |

### Environment Variable Precedence

1. Command-line arguments (`-e KEY=VALUE`) take highest precedence
2. User config file takes second precedence
3. System defaults take lowest precedence

### Security Considerations

- Configuration file permissions are set to 600 (user read/write only)
- Sensitive values can be referenced from environment variables: `${ENV_VAR}`
- API keys and secrets are never logged or displayed in verbose output

### CLI Configuration Commands

```bash
# View entire configuration
cubbi config list

# Get specific configuration value
cubbi config get defaults.driver

# Set configuration value (using simplified naming)
cubbi config set langfuse.url "https://cloud.langfuse.com"
cubbi config set openai.api_key "sk-..."

# Network configuration
cubbi config network list                   # List default networks
cubbi config network add example-network    # Add a network to defaults
cubbi config network remove example-network # Remove a network from defaults

# Reset configuration to defaults
cubbi config reset
```

## CLI Tool Commands

### Basic Commands

```bash
# Create a new session locally (shorthand)
cubbi

# List active sessions on local system
cubbi session list

# Create a new session locally
cubbi session create [OPTIONS]

# Create a session with a specific image
cubbi session create --image goose

# Create a session with a specific project repository
cubbi session create --image goose --project github.com/hello/private

# Create a session with external networks
cubbi session create --network teamnet --network othernetwork

# Create a session with a project (shorthand)
cubbi git@github.com:hello/private

# Close a specific session
cubbi session close <id>

# Connect to an existing session
cubbi session connect <id>

```

### Remote Management

```bash
# Add a remote Cubbi service
cubbi remote add <name> <url>

# List configured remote services
cubbi remote list

# Remove a remote service
cubbi remote remove <name>

# Authenticate with a remote service
cubbi -r <remote_name> auth

# Create a session on a remote service
cubbi -r <remote_name> [session create]

# List sessions on a remote service
cubbi -r <remote_name> session list
```

### Environment Variables

```bash
# Set environment variables for a session
cubbi session create -e VAR1=value1 -e VAR2=value2

# Set environment variables for a remote session
cubbi -r <remote_name> session create -e VAR1=value1
```

### Logging

```bash
# Stream logs from a session
cubbi session logs <id>

# Stream logs with follow option
cubbi session logs <id> -f
```

## Cubbi Service Specification

### Overview

The Cubbi Service is a web service that manages ephemeral containers in a Docker-in-Docker environment. It provides a REST API for container lifecycle management, authentication, and real-time log streaming.

### API Endpoints

#### Authentication

```
POST /auth/login        - Initiate Authentik authentication flow
POST /auth/callback     - Handle Authentik OAuth callback
POST /auth/refresh      - Refresh an existing token
POST /auth/logout       - Invalidate current token
```

### Authentik Integration

The Cubbi Service integrates with Authentik at https://authentik.monadical.io using OAuth 2.0:

1. **Application Registration**:
   - Cubbi Service is registered as an OAuth application in Authentik
   - Configured with redirect URI to `/auth/callback`
   - Assigned appropriate scopes for user identification

2. **Authentication Flow**:
   - User initiates authentication via CLI
   - Cubbi CLI opens browser to Authentik authorization URL
   - User logs in through Authentik's interface
   - Authentik redirects to callback URL with authorization code
   - Cubbi Service exchanges code for access and refresh tokens
   - CLI receives and securely stores tokens

3. **Token Management**:
   - Access tokens used for API authorization
   - Refresh tokens used to obtain new access tokens
   - Tokens are encrypted at rest in CLI configuration

#### Sessions

```
GET /sessions - List all sessions
POST /sessions - Create a new session
GET /sessions/{id} - Get session details
DELETE /sessions/{id} - Terminate a session
POST /sessions/{id}/connect - Establish connection to session
GET /sessions/{id}/logs - Stream session logs
```

#### Images

```
GET /images - List available images
GET /images/{name} - Get image details
```

#### Projects

```
GET /projects - List all projects
POST /projects - Add a new project
GET /projects/{id} - Get project details
PUT /projects/{id} - Update project details
DELETE /projects/{id} - Remove a project
```

### Service Configuration

```yaml
# cubbi-service.yaml
server:
  port: 3000
  host: 0.0.0.0

docker:
  socket: /var/run/docker.sock
  network: cubbi-network

auth:
  provider: authentik
  url: https://authentik.monadical.io
  clientId: cubbi-service

logging:
  providers:
    - type: fluentd
      url: http://fluentd.example.com:24224
    - type: langfuse
      url: https://cloud.langfuse.com
      public_key: ${LANGFUSE_INIT_PROJECT_PUBLIC_KEY}
      secret_key: ${LANGFUSE_INIT_PROJECT_SECRET_KEY}

images:
  - name: goose
    image: monadical/cubbi-goose:latest
  - name: aider
    image: monadical/cubbi-aider:latest
  - name: claude-code
    image: monadical/cubbi-claude-code:latest

projects:
  storage:
    type: encrypted
    key: ${PROJECT_ENCRYPTION_KEY}
  default_ssh_scan:
    - github.com
    - gitlab.com
    - bitbucket.org
```

### Docker-in-Docker Implementation

The Cubbi Service runs in a container with access to the host's Docker socket, allowing it to create and manage sibling containers. This approach provides:

1. Isolation between containers
2. Simple lifecycle management
3. Resource constraints for security

### Connection Handling

For remote connections to containers, the service provides two methods:

1. **WebSocket Terminal**: Browser-based terminal access
2. **SSH Server**: Each container runs an SSH server for CLI access

### Logging Implementation

The Cubbi Service implements log collection and forwarding:

1. Container logs are captured using Docker's logging drivers
2. Logs are forwarded to configured providers (Fluentd, Langfuse)
3. Real-time log streaming is available via WebSockets

## Project Management

### Persistent Project Configuration

Cubbi provides persistent storage for project-specific configurations that need to survive container restarts. This is implemented through a dedicated volume mount and symlink system:

1. **Configuration Storage**:
   - Each project has a dedicated configuration directory on the host at `~/.cubbi/projects/<project-hash>/config`
   - For projects specified by URL, the hash is derived from the repository URL
   - For local projects, the hash is derived from the absolute path of the local directory
   - This directory is mounted into the container at `/cubbi-config`

2. **Image Configuration**:
   - Each image can specify configuration files/directories that should persist across sessions
   - These are defined in the image's `cubbi-image.yaml` file in the `persistent_configs` section
   - Example for Goose image:
     ```yaml
     persistent_configs:
       - source: "/app/.goose"         # Path in container
         target: "/cubbi-config/goose"    # Path in persistent storage
         type: "directory"             # directory or file
         description: "Goose memory and configuration"
     ```

3. **Automatic Symlinking**:
   - During container initialization, the system:
     - Creates all target directories in the persistent storage
     - Creates symlinks from the source paths to the target paths
   - This makes the persistence transparent to the application

4. **Environment Variables**:
   - Container has access to configuration location via environment variables:
     ```
     CUBBI_CONFIG_DIR=/cubbi-config
     CUBBI_IMAGE_CONFIG_DIR=/cubbi-config/<image-name>
     ```

This ensures that important configurations like Goose's memory store, authentication tokens, and other state information persist between container sessions while maintaining isolation between different projects.

### Adding Projects

Users can add projects with associated credentials:

```bash
# Add a project with SSH key
cubbi project add github.com/hello/private --ssh-key ~/.ssh/id_ed25519

# Add a project with token authentication
cubbi project add github.com/hello/private --token ghp_123456789

# List all projects
cubbi project list

# Remove a project
cubbi project remove github.com/hello/private
```

### Project Configuration

Projects are stored in the Cubbi service and referenced by their repository URL. The configuration includes:

```yaml
# Project configuration
id: github.com/hello/private
url: git@github.com:hello/private.git
type: git
auth:
  type: ssh
  key: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    ...encrypted key data...
    -----END OPENSSH PRIVATE KEY-----
  public_key: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...
```

## Image Implementation

### Image Structure

Each image is a Docker container with a standardized structure:

```
/
├── entrypoint.sh      # Container initialization
├── cubbi-init.sh      # Standardized initialization script
├── cubbi-image.yaml   # Image metadata and configuration
├── tool/              # AI tool installation
└── ssh/               # SSH server configuration
```

### Standardized Initialization Script

All images include a standardized `cubbi-init.sh` script that handles common initialization tasks:
```bash
#!/bin/bash

# Project initialization
if [ -n "$CUBBI_PROJECT_URL" ]; then
    echo "Initializing project: $CUBBI_PROJECT_URL"

    # Set up SSH key if provided
    if [ -n "$CUBBI_GIT_SSH_KEY" ]; then
        mkdir -p ~/.ssh
        echo "$CUBBI_GIT_SSH_KEY" > ~/.ssh/id_ed25519
        chmod 600 ~/.ssh/id_ed25519
        ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
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
fi

# Image-specific initialization continues...
```

### Image Configuration (cubbi-image.yaml)

```yaml
name: goose
description: Goose with MCP servers
version: 1.0.0
maintainer: team@monadical.com

init:
  pre_command: /cubbi-init.sh
  command: /entrypoint.sh

environment:
  - name: MCP_HOST
    description: MCP server host
    required: true
    default: http://localhost:8000

  - name: GOOSE_ID
    description: Goose instance ID
    required: false

  # Project environment variables
  - name: CUBBI_PROJECT_URL
    description: Project repository URL
    required: false

  - name: CUBBI_PROJECT_TYPE
    description: Project repository type (git, svn, etc.)
    required: false
    default: git

  - name: CUBBI_GIT_SSH_KEY
    description: SSH key for Git authentication
    required: false
    sensitive: true

  - name: CUBBI_GIT_TOKEN
    description: Token for Git authentication
    required: false
    sensitive: true

ports:
  - 8000   # Main application
  - 22     # SSH server

volumes:
  - mountPath: /app
    description: Application directory

persistent_configs:
  - source: "/app/.goose"
    target: "/cubbi-config/goose"
    type: "directory"
    description: "Goose memory and configuration"
```

### Example Built-in images

1. **goose**: Goose with MCP servers
2. **aider**: Aider coding assistant
3. **claude-code**: Claude Code environment
4. **custom**: Custom Dockerfile support

## Network Management

### Docker Network Integration

Cubbi provides flexible network management for containers:

1. **Default Cubbi Network**:
   - Each container is automatically connected to the Cubbi network (`cubbi-network` by default)
   - This ensures containers can communicate with each other

2. **External Network Connection**:
   - Containers can be connected to one or more external Docker networks
   - This allows integration with existing infrastructure (e.g., databases, web servers)
   - Networks can be specified at session creation time: `cubbi session create --network mynetwork`

3. **Default Networks Configuration**:
   - Users can configure default networks in their configuration
   - These networks will be used for all new sessions unless overridden
   - Managed with `cubbi config network` commands

4. **Network Command Examples**:
   ```bash
   # Use with session creation
   cubbi session create --network teamnet

   # Use with multiple networks
   cubbi session create --network teamnet --network dbnet

   # Configure default networks
   cubbi config network add teamnet
   ```

## Security Considerations

1. **Container Isolation**: Each session runs in an isolated container
2. **Authentication**: Integration with Authentik for secure authentication
3. **Resource Limits**: Configurable CPU, memory, and storage limits
4. **Network Isolation**: Internal Docker network for container-to-container communication with optional external network connections
5. **Encrypted Connections**: TLS for API connections and SSH for terminal access

## Deployment

### Cubbi Service Deployment

```yaml
# docker-compose.yml for Cubbi Service
version: '3.8'

services:
  cubbi-service:
    image: monadical/cubbi-service:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config:/app/config
    ports:
      - "3000:3000"
    environment:
      - AUTH_URL=https://authentik.monadical.io
      - LANGFUSE_API_KEY=your_api_key
    networks:
      - cubbi-network

networks:
  cubbi-network:
    driver: bridge
```

## Project Repository Integration Workflow

### Adding a Project Repository

1. User adds project repository with authentication:
   ```bash
   cubbi project add github.com/hello/private --ssh-key ~/.ssh/id_ed25519
   ```

2. Cubbi CLI reads the SSH key, encrypts it, and sends to Cubbi Service

3. Cubbi Service stores the project configuration securely

### Using a Project in a Session

1. User creates a session with a project:
   ```bash
   cubbi -r monadical git@github.com:hello/private
   ```

2. Cubbi Service:
   - Identifies the project from the URL
   - Retrieves project authentication details
   - Sets up environment variables:
     ```
     CUBBI_PROJECT_URL=git@github.com:hello/private
     CUBBI_PROJECT_TYPE=git
     CUBBI_GIT_SSH_KEY=<contents of the SSH key>
     ```
   - Creates container with these environment variables

3. Container initialization:
   - The standardized `cubbi-init.sh` script detects the project environment variables
   - Sets up SSH key or token authentication
   - Clones the repository to `/app`
   - Runs any project-specific initialization scripts

4. User can immediately begin working with the repository

## Implementation Roadmap

1. **Phase 1**: Local CLI tool with Docker integration
2. **Phase 2**: Cubbi Service REST API with basic container management
3. **Phase 3**: Authentication and secure connections
4. **Phase 4**: Project management functionality
5. **Phase 5**: Image implementation (Goose, Aider, Claude Code)
6. **Phase 6**: Logging integration with Fluentd and Langfuse
7. **Phase 7**: CLI remote connectivity improvements
8. **Phase 8**: Additional images and extensibility features
