<div align="center">

# Cubbi - Container Tool

Cubbi is a command-line tool for managing ephemeral containers that run AI tools and development environments. It works with both local Docker and a dedicated remote web service that manages containers in a Docker-in-Docker (DinD) environment. Cubbi also supports connecting to MCP (Model Control Protocol) servers to extend AI tools with additional capabilities.

![PyPI - Version](https://img.shields.io/pypi/v/cubbi)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cubbi)
[![Tests](https://github.com/monadical-sas/cubbi/actions/workflows/pytests.yml/badge.svg?branch=main&event=push)](https://github.com/monadical-sas/cubbi/actions/workflows/pytests.yml)

</div>

## 🚀 Quick Reference

- `cubbi session create` - Create a new session
- `cubbix` - Shortcut for `cubbi session create`
- `cubbix .` - Mount the current directory
- `cubbix /path/to/dir` - Mount a specific directory
- `cubbix https://github.com/user/repo` - Clone a repository

## 📋 Requirements

- [uv](https://docs.astral.sh/uv/)

## 📥 Installation

```bash
# Clone the repository
git clone https://github.com/monadical/cubbi.git

# Install the tool locally
# (with editable, so you can update the code and work with it)
cd cubbi
uv tool install --with-editable . .

# Then you could use the tool as `cubbi`
cubbi --help
```

Important: compile your first image

```bash
cubbi image build goose
```

## 📚 Basic Usage

```bash
# Show help message (displays available commands)
cubbi

# Create a new session with the default image (using cubbix alias)
cubbix

# Create a session and run an initial command before the shell starts
cubbix --run "echo 'Setup complete'; ls -l"

# List all active sessions
cubbi session list

# Connect to a specific session
cubbi session connect SESSION_ID

# Close a session when done
cubbi session close SESSION_ID

# Create a session with a specific image
cubbix --image goose

# Create a session with environment variables
cubbix -e VAR1=value1 -e VAR2=value2

# Mount custom volumes (similar to Docker's -v flag)
cubbix -v /local/path:/container/path
cubbix -v ~/data:/data -v ./configs:/etc/app/config

# Mount a local directory (current directory or specific path)
cubbix .
cubbix /path/to/project

# Connect to external Docker networks
cubbix --network teamnet --network dbnet

# Connect to MCP servers for extended capabilities
cubbix --mcp github --mcp jira

# Clone a Git repository
cubbix https://github.com/username/repo

# Using the cubbix shortcut (equivalent to cubbi session create)
cubbix                        # Creates a session without mounting anything
cubbix .                      # Mounts the current directory
cubbix /path/to/project       # Mounts the specified directory
cubbix https://github.com/username/repo  # Clones the repository

# Shorthand with MCP servers
cubbix https://github.com/username/repo --mcp github

# Shorthand with an initial command
cubbix . --run "apt-get update && apt-get install -y my-package"

# Enable SSH server in the container
cubbix --ssh
```

## 🖼️ Image Management

Cubbi includes an image management system that allows you to build, manage, and use Docker images for different AI tools:

```bash
# List available images
cubbi image list

# Get detailed information about an image
cubbi image info goose

# Build an image
cubbi image build goose

# Build and push an image
cubbi image build goose --push
```

Images are defined in the `cubbi/images/` directory, with each subdirectory containing:

- `Dockerfile`: Docker image definition
- `entrypoint.sh`: Container entrypoint script
- `cubbi-init.sh`: Standardized initialization script
- `cubbi-image.yaml`: Image metadata and configuration
- `README.md`: Image documentation

Cubbi automatically discovers and loads image definitions from the YAML files.
```

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

## ⚙️ Configuration

Cubbi supports user-specific configuration via a YAML file located at `~/.config/cubbi/config.yaml`. This allows you to set default values and configure service credentials.

### Managing Configuration

```bash
# View all configuration
cubbi config list

# Get a specific configuration value
cubbi config get langfuse.url

# Set configuration values
cubbi config set langfuse.url "https://cloud.langfuse.com"
cubbi config set langfuse.public_key "pk-lf-..."
cubbi config set langfuse.secret_key "sk-lf-..."

# Set API keys for various services
cubbi config set openai.api_key "sk-..."
cubbi config set anthropic.api_key "sk-ant-..."

# Reset configuration to defaults
cubbi config reset
```

### Default Networks Configuration

You can configure default networks that will be applied to every new session:

```bash
# List default networks
cubbi config network list

# Add a network to defaults
cubbi config network add teamnet

# Remove a network from defaults
cubbi config network remove teamnet
```

### Default Volumes Configuration

You can configure default volumes that will be automatically mounted in every new session:

```bash
# List default volumes
cubbi config volume list

# Add a volume to defaults
cubbi config volume add /local/path:/container/path

# Remove a volume from defaults (will prompt if multiple matches found)
cubbi config volume remove /local/path
```

Default volumes will be combined with any volumes specified using the `-v` flag when creating a session.

### Default MCP Servers Configuration

You can configure default MCP servers that sessions will automatically connect to:

```bash
# List default MCP servers
cubbi config mcp list

# Add an MCP server to defaults
cubbi config mcp add github

# Remove an MCP server from defaults
cubbi config mcp remove github
```

When adding new MCP servers, they are added to defaults by default. Use the `--no-default` flag to prevent this:

```bash
# Add an MCP server without adding it to defaults
cubbi mcp add github ghcr.io/mcp/github:latest --no-default
cubbi mcp add-remote jira https://jira-mcp.example.com/sse --no-default
```

When creating sessions, if no MCP server is specified with `--mcp`, the default MCP servers will be used automatically.

### External Network Connectivity

Cubbi containers can connect to external Docker networks, allowing them to communicate with other services in those networks:

```bash
# Create a session connected to external networks
cubbi session create --network teamnet --network dbnet
```

**Important**: Networks must be "attachable" to be joined by Cubbi containers. Here's how to create attachable networks:

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
    attachable: true  # This is required for Cubbi containers to connect
```

### Service Credentials

Service credentials like API keys configured in `~/.config/cubbi/config.yaml` are automatically passed to containers as environment variables:

| Config Setting | Environment Variable |
|----------------|---------------------|
| `langfuse.url` | `LANGFUSE_URL` |
| `langfuse.public_key` | `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` |
| `langfuse.secret_key` | `LANGFUSE_INIT_PROJECT_SECRET_KEY` |
| `openai.api_key` | `OPENAI_API_KEY` |
| `anthropic.api_key` | `ANTHROPIC_API_KEY` |
| `openrouter.api_key` | `OPENROUTER_API_KEY` |
| `google.api_key` | `GOOGLE_API_KEY` |

## 🌐 MCP Server Management

MCP (Model Control Protocol) servers provide tool-calling capabilities to AI models, enhancing their ability to interact with external services, databases, and systems. Cubbi supports multiple types of MCP servers:

1. **Remote HTTP SSE servers** - External MCP servers accessed over HTTP
2. **Docker-based MCP servers** - Local MCP servers running in Docker containers
3. **Proxy-based MCP servers** - Local MCP servers with an SSE proxy for stdio-to-SSE conversion

### Managing MCP Servers

```bash
# List all configured MCP servers and their status
cubbi mcp list

# View detailed status of an MCP server
cubbi mcp status github

# Start/stop/restart individual MCP servers
cubbi mcp start github
cubbi mcp stop github
cubbi mcp restart github

# Start all MCP servers at once
cubbi mcp start --all

# Stop and remove all MCP servers at once
cubbi mcp stop --all

# Run the MCP Inspector to visualize and interact with MCP servers
# It automatically joins all MCP networks for seamless DNS resolution
# Uses two ports: frontend UI (default: 5173) and backend API (default: 3000)
cubbi mcp inspector

# Run the MCP Inspector with custom ports
cubbi mcp inspector --client-port 6173 --server-port 6174

# Run the MCP Inspector in detached mode
cubbi mcp inspector --detach

# Stop the MCP Inspector
cubbi mcp inspector --stop

# View MCP server logs
cubbi mcp logs github

# Remove an MCP server configuration
cubbi mcp remove github
```

### Adding MCP Servers

Cubbi supports different types of MCP servers:

```bash
# Add a remote HTTP SSE MCP server
cubbi mcp remote add github http://my-mcp-server.example.com/sse --header "Authorization=Bearer token123"

# Add a Docker-based MCP server
cubbi mcp docker add github mcp/github:latest --command "github-mcp" --env GITHUB_TOKEN=ghp_123456

# Add a proxy-based MCP server (for stdio-to-SSE conversion)
cubbi mcp add github ghcr.io/mcp/github:latest --proxy-image ghcr.io/sparfenyuk/mcp-proxy:latest --command "github-mcp" --sse-port 8080 --no-default
```

### Using MCP Servers with Sessions

MCP servers can be attached to sessions when they are created:

```bash
# Create a session with a single MCP server
cubbi session create --mcp github

# Create a session with multiple MCP servers
cubbi session create --mcp github --mcp jira

# Using MCP with a project repository
cubbi github.com/username/repo --mcp github
```

MCP servers are persistent and can be shared between sessions. They continue running even when sessions are closed, allowing for efficient reuse across multiple sessions.
