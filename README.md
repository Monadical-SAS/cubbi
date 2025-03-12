# MC - Monadical Container Tool

MC (Monadical Container) is a command-line tool for managing ephemeral
containers that run AI tools and development environments. It works with both
local Docker and a dedicated remote web service that manages containers in a
Docker-in-Docker (DinD) environment.

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
# Create a new session with the default driver
# mc create session -- is the full command
mc

# List all active sessions
mc session list

# Connect to a specific session
mc session connect SESSION_ID

# Close a session when done
mc session close SESSION_ID

# Create a session with a specific driver
mc session create --driver goose

# Create a session with environment variables
mc session create -e VAR1=value1 -e VAR2=value2

# Mount custom volumes (similar to Docker's -v flag)
mc session create -v /local/path:/container/path
mc session create -v ~/data:/data -v ./configs:/etc/app/config

# Connect to external Docker networks
mc session create --network teamnet --network dbnet

# Shorthand for creating a session with a project repository
mc github.com/username/repo
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
