# MC - Monadical Container Tool

MC (Monadical Container) is a command-line tool for managing ephemeral
containers that run AI tools and development environments. It works with both
local Docker and a dedicated remote web service that manages containers in a
Docker-in-Docker (DinD) environment. MC also supports connecting to MCP (Model Context Protocol) servers to extend AI tools with additional capabilities.

## Quick Reference

- `mc session create` - Create a new session
- `mcx` - Shortcut for `mc session create`
- `mcx .` - Mount the current directory
- `mcx /path/to/dir` - Mount a specific directory
- `mcx https://github.com/user/repo` - Clone a repository

## Requirements

- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
# Clone the repository
git clone https://github.com/monadical/mcontainer.git

# Install the tool locally
# (with editable, so you can update the code and work with it)
cd mcontainer
uv tool install --with-editable . .

# Then you could use the tool as `mc`
mc --help
```

## Basic Usage

```bash
# Show help message (displays available commands)
mc

# Create a new session with the default driver (using mcx alias)
mcx

# Create a session and run an initial command before the shell starts
mcx --run "echo 'Setup complete'; ls -l"

# List all active sessions
mc session list

# Connect to a specific session
mc session connect SESSION_ID

# Close a session when done
mc session close SESSION_ID

# Create a session with a specific driver
mcx --driver goose

# Create a session with environment variables
mcx -e VAR1=value1 -e VAR2=value2

# Mount custom volumes (similar to Docker's -v flag)
mcx -v /local/path:/container/path
mcx -v ~/data:/data -v ./configs:/etc/app/config

# Mount a local directory (current directory or specific path)
mcx .
mcx /path/to/project

# Connect to external Docker networks
mcx --network teamnet --network dbnet

# Connect to MCP servers for extended capabilities
mcx --mcp github --mcp jira

# Clone a Git repository
mcx https://github.com/username/repo

# Using the mcx shortcut (equivalent to mc session create)
mcx                        # Creates a session without mounting anything
mcx .                      # Mounts the current directory
mcx /path/to/project       # Mounts the specified directory
mcx https://github.com/username/repo  # Clones the repository

# Shorthand with MCP servers
mcx https://github.com/username/repo --mcp github

# Shorthand with an initial command
mcx . --run "apt-get update && apt-get install -y my-package"

# Enable SSH server in the container
mcx --ssh
```

## Driver Management

MC includes a driver management system that allows you to build, manage, and use Docker images for different AI tools:

```bash
# List available drivers
mc driver list

# Get detailed information about a driver
mc driver info goose

# Build a driver image
mc driver build goose

# Build and push a driver image
mc driver build goose --push
```

Drivers are defined in the `mcontainer/drivers/` directory, with each subdirectory containing:

- `Dockerfile`: Docker image definition
- `entrypoint.sh`: Container entrypoint script
- `mc-init.sh`: Standardized initialization script
- `mc-driver.yaml`: Driver metadata and configuration
- `README.md`: Driver documentation

MC automatically discovers and loads driver definitions from the YAML files.

## Development

```bash
# Run the tests
uv run -m pytest

# Run linting
uvx ruff check .

# Run type checking
uvx mypy .

# Format code
uvx ruff format .
```

## Configuration

MC supports user-specific configuration via a YAML file located at `~/.config/mc/config.yaml`. This allows you to set default values and configure service credentials.

### Managing Configuration

```bash
# View all configuration
mc config list

# Get a specific configuration value
mc config get langfuse.url

# Set configuration values
mc config set langfuse.url "https://cloud.langfuse.com"
mc config set langfuse.public_key "pk-lf-..."
mc config set langfuse.secret_key "sk-lf-..."

# Set API keys for various services
mc config set openai.api_key "sk-..."
mc config set anthropic.api_key "sk-ant-..."

# Reset configuration to defaults
mc config reset
```

### Default Networks Configuration

You can configure default networks that will be applied to every new session:

```bash
# List default networks
mc config network list

# Add a network to defaults
mc config network add teamnet

# Remove a network from defaults
mc config network remove teamnet
```

### Default Volumes Configuration

You can configure default volumes that will be automatically mounted in every new session:

```bash
# List default volumes
mc config volume list

# Add a volume to defaults
mc config volume add /local/path:/container/path

# Remove a volume from defaults (will prompt if multiple matches found)
mc config volume remove /local/path
```

Default volumes will be combined with any volumes specified using the `-v` flag when creating a session.

### Default MCP Servers Configuration

You can configure default MCP servers that sessions will automatically connect to:

```bash
# List default MCP servers
mc config mcp list

# Add an MCP server to defaults
mc config mcp add github

# Remove an MCP server from defaults
mc config mcp remove github
```

When adding new MCP servers, they are added to defaults by default. Use the `--no-default` flag to prevent this:

```bash
# Add an MCP server without adding it to defaults
mc mcp add github ghcr.io/mcp/github:latest --no-default
mc mcp add-remote jira https://jira-mcp.example.com/sse --no-default
```

When creating sessions, if no MCP server is specified with `--mcp`, the default MCP servers will be used automatically.

### External Network Connectivity

MC containers can connect to external Docker networks, allowing them to communicate with other services in those networks:

```bash
# Create a session connected to external networks
mc session create --network teamnet --network dbnet
```

**Important**: Networks must be "attachable" to be joined by MC containers. Here's how to create attachable networks:

```bash
# Create an attachable network with Docker
docker network create --driver bridge --attachable teamnet

# Example docker-compose.yml with attachable network
# docker-compose.yml
version: '3'
services:
  web:
    image: nginx
    networks:
      - teamnet

networks:
  teamnet:
    driver: bridge
    attachable: true  # This is required for MC containers to connect
```

### Service Credentials

Service credentials like API keys configured in `~/.config/mc/config.yaml` are automatically passed to containers as environment variables:

| Config Setting | Environment Variable |
|----------------|---------------------|
| `langfuse.url` | `LANGFUSE_URL` |
| `langfuse.public_key` | `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` |
| `langfuse.secret_key` | `LANGFUSE_INIT_PROJECT_SECRET_KEY` |
| `openai.api_key` | `OPENAI_API_KEY` |
| `anthropic.api_key` | `ANTHROPIC_API_KEY` |
| `openrouter.api_key` | `OPENROUTER_API_KEY` |
| `google.api_key` | `GOOGLE_API_KEY` |

## MCP Server Management

MCP (Model Context Protocol) servers provide tool-calling capabilities to AI models, enhancing their ability to interact with external services, databases, and systems. MC supports multiple types of MCP servers:

1. **Remote HTTP SSE servers** - External MCP servers accessed over HTTP
2. **Docker-based MCP servers** - Local MCP servers running in Docker containers
3. **Proxy-based MCP servers** - Local MCP servers with an SSE proxy for stdio-to-SSE conversion

### Managing MCP Servers

```bash
# List all configured MCP servers and their status
mc mcp list

# View detailed status of an MCP server
mc mcp status github

# Start/stop/restart individual MCP servers
mc mcp start github
mc mcp stop github
mc mcp restart github

# Start all MCP servers at once
mc mcp start --all

# Stop and remove all MCP servers at once
mc mcp stop --all

# Run the MCP Inspector to visualize and interact with MCP servers
# It automatically joins all MCP networks for seamless DNS resolution
# Uses two ports: frontend UI (default: 5173) and backend API (default: 3000)
mc mcp inspector

# Run the MCP Inspector with custom ports
mc mcp inspector --client-port 6173 --server-port 6174

# Run the MCP Inspector in detached mode
mc mcp inspector --detach

# Stop the MCP Inspector
mc mcp inspector --stop

# View MCP server logs
mc mcp logs github

# Remove an MCP server configuration
mc mcp remove github
```

### Adding MCP Servers

MC supports different types of MCP servers:

```bash
# Add a remote HTTP SSE MCP server
mc mcp remote add github http://my-mcp-server.example.com/sse --header "Authorization=Bearer token123"

# Add a Docker-based MCP server
mc mcp docker add github mcp/github:latest --command "github-mcp" --env GITHUB_TOKEN=ghp_123456

# Add a proxy-based MCP server (for stdio-to-SSE conversion)
mc mcp add github ghcr.io/mcp/github:latest --proxy-image ghcr.io/sparfenyuk/mcp-proxy:latest --command "github-mcp" --sse-port 8080 --no-default
```

### Using MCP Servers with Sessions

MCP servers can be attached to sessions when they are created:

```bash
# Create a session with a single MCP server
mc session create --mcp github

# Create a session with multiple MCP servers
mc session create --mcp github --mcp jira

# Using MCP with a project repository
mc github.com/username/repo --mcp github
```

MCP servers are persistent and can be shared between sessions. They continue running even when sessions are closed, allowing for efficient reuse across multiple sessions.
