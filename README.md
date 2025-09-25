<div align="center">

# Cubbi - Container Tool

Cubbi is a command-line tool for managing ephemeral containers that run AI tools and development environments, with support for MCP servers. It supports [Aider](https://github.com/Aider-AI/aider), [Crush](https://github.com/charmbracelet/crush), [Claude Code](https://github.com/anthropics/claude-code), [Goose](https://github.com/block/goose), [Opencode](https://github.com/sst/opencode).

![PyPI - Version](https://img.shields.io/pypi/v/cubbi)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cubbi)
[![Tests](https://github.com/monadical-sas/cubbi/actions/workflows/pytests.yml/badge.svg?branch=main&event=push)](https://github.com/monadical-sas/cubbi/actions/workflows/pytests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 🚀 Quick Reference

- `cubbi session create` - Create a new session
- `cubbix` - Shortcut for `cubbi session create`
- `cubbix .` - Mount the current directory
- `cubbix /path/to/dir` - Mount a specific directory

## 📋 Requirements

- [Docker](https://www.docker.com/)
- [uv](https://astral.sh/uv)

## 📥 Installation

```bash
# Via uv
uv tool install cubbi

# Without installation
# (meaning all commands below must be prefixed with `uvx`)
uvx cubbi
```

Then compile your first image:

```bash
cubbi image build goose
cubbi image build opencode
cubbi image build crush
```

### For Developers

If you are looking to contribute to the development, you will need to use `uv` as well:

```bash
git clone https://github.com/monadical-sas/cubbi
cd cubbi
uv tool install --with-editable . .
# You'll have cubbi and cubbix executable files in your PATH, pointing to the local installation.
```

## 📚 Basic Usage

```bash
# Show help message (displays available commands)
cubbi

# Create a new session with the default image (using cubbix alias)
cubbix

# Create a session and run an initial command before the shell starts
cubbix --run "ls -l"

# Create a session, run a command, and exit (no shell prompt)
cubbix --run "ls -l" --no-shell

# List all active sessions
cubbi session list

# Connect to a specific session
cubbi session connect SESSION_ID

# Close a session when done
cubbi session close SESSION_ID

# Close a session quickly (kill instead of graceful stop)
cubbi session close SESSION_ID --kill

# Close all sessions at once
cubbi session close --all

# Close all sessions quickly
cubbi session close --all --kill

# Create a session with a specific image
cubbix --image goose
cubbix --image opencode
cubbix --image crush

# Create a session with environment variables
cubbix -e VAR1=value1 -e VAR2=value2

# Mount custom volumes (similar to Docker's -v flag)
cubbix -v /local/path:/container/path
cubbix -v ~/data:/data -v ./configs:/etc/app/config

# Mount a local directory (current directory or specific path)
cubbix .
cubbix /path/to/project

# Forward ports from container to host
cubbix --port 8000                    # Forward port 8000
cubbix --port 8000,3000,5173         # Forward multiple ports (comma-separated)
cubbix --port 8000 --port 3000       # Forward multiple ports (repeated flag)

# Connect to external Docker networks
cubbix --network teamnet --network dbnet

# Restrict network access to specific domains
cubbix --domains github.com --domains "api.example.com:443"

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

# Execute a command and exit without starting a shell
cubbix . --run "python script.py" --no-shell

# Enable SSH server in the container
cubbix --ssh
```

## 🖼️ Image Management

Cubbi includes an image management system that allows you to build, manage, and use Docker images for different AI tools

**Supported Images**

| Image Name | Langtrace Support | Single Prompt Command |
|------------|-------------------|----------------------|
| goose      | yes               | `goose run -t 'prompt' --no-session --quiet` |
| opencode   | no                | `opencode run -m MODEL 'prompt'` |
| claudecode | no                | `claude -p 'prompt'` |
| aider      | no                | `aider --message 'prompt' --yes-always --no-fancy-input` |
| crush      | no                | `crush run 'prompt'` |

**Automated Testing:**

Each image can be tested with single prompt commands using different models:

```bash
# Test a single image with a specific model
cubbix -i goose -m anthropic/claude-sonnet-4-20250514 --no-connect --no-shell --run "goose run -t 'What is 2+2?' --no-session --quiet"

# Test aider with non-interactive flags
cubbix -i aider -m openai/gpt-4o --no-connect --no-shell --run "aider --message 'What is 2+2?' --yes-always --no-fancy-input --no-check-update"

# Test claude-code (note: binary name is 'claude', not 'claude-code')
cubbix -i claudecode -m anthropic/claude-sonnet-4-20250514 --no-connect --no-shell --run "claude -p 'What is 2+2?'"

# Test opencode with model specification
cubbix -i opencode -m anthropic/claude-sonnet-4-20250514 --no-connect --no-shell --run "opencode run -m anthropic/claude-sonnet-4-20250514 'What is 2+2?'"

# Test crush
cubbix -i crush -m anthropic/claude-sonnet-4-20250514 --no-connect --no-shell --run "crush run 'What is 2+2?'"

# Run comprehensive test suite (requires test.sh script)
./test.sh  # Tests all images with multiple models: anthropic/claude-sonnet-4-20250514, openai/gpt-4o, openrouter/openai/gpt-4o, litellm/gpt-oss:120b
```

```bash
# List available images
cubbi image list

# Get detailed information about an image
cubbi image info goose
cubbi image info opencode
cubbi image info crush

# Build an image
cubbi image build goose
cubbi image build opencode
cubbi image build crush

# Build an image without using cache (force fresh build)
cubbi image build --no-cache goose
```

Images are defined in the `cubbi/images/` directory, with each subdirectory containing:

- `Dockerfile`: Docker image definition
- `entrypoint.sh`: Container entrypoint script
- `cubbi-init.sh`: Standardized initialization script
- `cubbi_image.yaml`: Image metadata and configuration
- `README.md`: Image documentation

Cubbi automatically discovers and loads image definitions from the YAML files.
```

## Development

```bash
# Run the tests
uv run -m pytest

# Run linting
uvx ruff check .

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

### Default Ports Configuration

You can configure default ports that will be automatically forwarded in every new session:

```bash
# List default ports
cubbi config port list

# Add a single port to defaults
cubbi config port add 8000

# Add multiple ports to defaults (comma-separated)
cubbi config port add 8000,3000,5173

# Remove a port from defaults
cubbi config port remove 8000
```

Default ports will be combined with any ports specified using the `--port` flag when creating a session.

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
cubbi mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=xxxx github mcp/github --no-default
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
2. **Docker-based MCP servers** - MCP servers running in Docker containers, with a SSE proxy for stdio-to-SSE conversion
3. **Local MCP servers** - MCP servers running as local processes on your host machine

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
# Docker-based MCP server (with proxy)
cubbi mcp add fetch mcp/fetch
cubbi mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=xxxx mcp/github mcp/github-proxy

# Remote HTTP SSE server
cubbi mcp add-remote myserver https://myssemcp.com/sse

# Local MCP server (runs as a local process)
cubbi mcp add-local mylocalmcp /path/to/mcp-executable
cubbi mcp add-local mylocalmcp /usr/local/bin/mcp-tool --args "--config" --args "/etc/mcp.conf"
cubbi mcp add-local mylocalmcp npx --args "@modelcontextprotocol/server-filesystem" --args "/path/to/data"

# Add environment variables to local MCP servers
cubbi mcp add-local mylocalmcp /path/to/mcp-server -e API_KEY=xxx -e BASE_URL=https://api.example.com

# Prevent adding to default MCPs
cubbi mcp add myserver mcp/server --no-default
cubbi mcp add-local mylocalmcp /path/to/executable --no-default
```

### Using MCP Servers with Sessions

MCP servers can be attached to sessions when they are created:

```bash
# Create a session with a single MCP server
cubbi session create --mcp github

# Create a session with multiple MCP servers
cubbi session create --mcp github --mcp jira
```

MCP servers are persistent and can be shared between sessions. They continue running even when sessions are closed, allowing for efficient reuse across multiple sessions.

## 📜 License

Cubbi is licensed under the [MIT License](LICENSE).
