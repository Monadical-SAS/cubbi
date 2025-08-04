# Crush Image for Cubbi

This image provides a containerized environment for running [Crush](https://github.com/charmbracelet/crush), a terminal-based AI coding assistant.

## Features

- Pre-configured environment for Crush AI coding assistant
- Multi-model support (OpenAI, Anthropic, Groq)
- JSON-based configuration
- MCP server integration support
- Session preservation across runs

## Environment Variables

### AI Provider Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for crush | No | - |
| `ANTHROPIC_API_KEY` | Anthropic API key for crush | No | - |
| `GROQ_API_KEY` | Groq API key for crush | No | - |
| `OPENAI_URL` | Custom OpenAI-compatible API URL | No | - |
| `CUBBI_MODEL` | AI model to use with crush | No | - |
| `CUBBI_PROVIDER` | AI provider to use with crush | No | - |

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
cd cubbi/images/crush
docker build -t monadical/cubbi-crush:latest .
```

## Usage

```bash
# Create a new session with this image
cubbix -i crush

# Run crush with specific provider
cubbix -i crush -e CUBBI_PROVIDER=openai -e CUBBI_MODEL=gpt-4

# Test crush installation
cubbix -i crush --no-shell --run "crush --help"
```

## Configuration

Crush uses JSON configuration stored in `/home/cubbi/.config/crush/config.json`. The plugin automatically configures:

- AI providers based on available API keys
- Default models and providers from environment variables
- Session preservation settings
- MCP server integrations