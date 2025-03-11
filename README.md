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
mc session create

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

# Shorthand for creating a session with a project repository
mc github.com/username/repo

# Local development with API keys
# OPENAI_API_KEY, ANTHROPIC_API_KEY, and OPENROUTER_API_KEY from your
# local environment are automatically passed to the container
mc session create
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

Drivers are defined in the `drivers/` directory, with each subdirectory containing:

- `Dockerfile`: Docker image definition
- `entrypoint.sh`: Container entrypoint script
- `mai-init.sh`: Standardized initialization script
- `mai-driver.yaml`: Driver metadata and configuration
- `README.md`: Driver documentation

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
