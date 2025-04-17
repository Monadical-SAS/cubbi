# Goose Image for MC

This image provides a containerized environment for running [Goose](https://goose.ai).

## Features

- Pre-configured environment for Goose AI
- Self-hosted instance integration
- SSH access
- Git repository integration
- Langfuse logging support

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` | Langfuse public key | No |
| `LANGFUSE_INIT_PROJECT_SECRET_KEY` | Langfuse secret key | No |
| `LANGFUSE_URL` | Langfuse API URL | No |
| `MC_PROJECT_URL` | Project repository URL | No |
| `MC_GIT_SSH_KEY` | SSH key for Git authentication | No |
| `MC_GIT_TOKEN` | Token for Git authentication | No |

## Build

To build this image:

```bash
cd drivers/goose
docker build -t monadical/mc-goose:latest .
```

## Usage

```bash
# Create a new session with this image
mc session create --driver goose

# Create with project repository
mc session create --driver goose --project github.com/username/repo
```
