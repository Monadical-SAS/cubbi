# MC - Monadical Container Tool

MC (Monadical Container) is a command-line tool for managing ephemeral containers that run AI tools and development environments. It works with both local Docker and a dedicated remote web service that manages containers in a Docker-in-Docker (DinD) environment.

## Installation

```bash
# Clone the repository
git clone https://github.com/monadical/mc.git
cd mc

# Install with uv
uv sync
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
uv run --with=ruff ruff check .

# Run type checking
uv run --with=mypy mypy .

# Format code
uv run --with=ruff ruff format .
```

## License

See LICENSE file for details.