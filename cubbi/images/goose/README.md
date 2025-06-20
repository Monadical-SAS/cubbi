# Goose Image for Cubbi

This image provides a containerized environment for running [Goose](https://goose.ai).

## Features

- Pre-configured environment for Goose AI
- Langfuse logging support

## Environment Variables

### Goose Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CUBBI_MODEL` | Model to use with Goose | No | - |
| `CUBBI_PROVIDER` | Provider to use with Goose | No | - |

### Langfuse Integration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` | Langfuse public key | No | - |
| `LANGFUSE_INIT_PROJECT_SECRET_KEY` | Langfuse secret key | No | - |
| `LANGFUSE_URL` | Langfuse API URL | No | `https://cloud.langfuse.com` |

### Cubbi Core Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CUBBI_USER_ID` | UID for the container user | No | `1000` |
| `CUBBI_GROUP_ID` | GID for the container user | No | `1000` |
| `CUBBI_RUN_COMMAND` | Command to execute after initialization | No | - |
| `CUBBI_NO_SHELL` | Exit after command execution | No | `false` |
| `CUBBI_CONFIG_DIR` | Directory for persistent configurations | No | `/cubbi-config` |
| `CUBBI_PERSISTENT_LINKS` | Semicolon-separated list of source:target symlinks | No | - |

### MCP Integration Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MCP_COUNT` | Number of available MCP servers | No |
| `MCP_NAMES` | JSON array of MCP server names | No |
| `MCP_{idx}_NAME` | Name of MCP server at index | No |
| `MCP_{idx}_TYPE` | Type of MCP server | No |
| `MCP_{idx}_HOST` | Hostname of MCP server | No |
| `MCP_{idx}_URL` | Full URL for remote MCP servers | No |

## Build

To build this image:

```bash
cd drivers/goose
docker build -t monadical/cubbi-goose:latest .
```

## Usage

```bash
# Create a new session with this image
cubbix -i goose
```
