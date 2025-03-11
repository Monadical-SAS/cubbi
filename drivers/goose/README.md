# Goose Driver for MC

This driver provides a containerized environment for running [Goose](https://goose.ai) with MCP servers.

## Features

- Pre-configured environment for Goose AI
- MCP server integration
- SSH access
- Git repository integration
- Langfuse logging support

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MCP_HOST` | MCP server host | Yes |
| `GOOSE_API_KEY` | Goose API key | Yes |
| `GOOSE_ID` | Goose instance ID | No |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | No |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | No |
| `LANGFUSE_HOST` | Langfuse API host | No |
| `MC_PROJECT_URL` | Project repository URL | No |
| `MC_GIT_SSH_KEY` | SSH key for Git authentication | No |
| `MC_GIT_TOKEN` | Token for Git authentication | No |

## Build

To build this driver:

```bash
cd drivers/goose
docker build -t monadical/mc-goose:latest .
```

## Usage

```bash
# Create a new session with this driver
mc session create --driver goose

# Create with specific MCP server
mc session create --driver goose -e MCP_HOST=http://mcp.example.com:8000

# Create with project repository
mc session create --driver goose --project github.com/username/repo
```