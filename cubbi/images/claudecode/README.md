# Claude Code for Cubbi

This image provides Claude Code (Anthropic's official CLI for Claude) in a Cubbi container environment.

## Overview

Claude Code is an interactive CLI tool that helps with software engineering tasks. This Cubbi image integrates Claude Code with secure API key management, persistent configuration, and enterprise features.

## Features

- **Claude Code CLI**: Full access to Claude's coding capabilities
- **Secure Authentication**: API key management through Cubbi's secure environment system
- **Persistent Configuration**: Settings and cache preserved across container restarts
- **Enterprise Support**: Bedrock and Vertex AI integration
- **Network Support**: Proxy configuration for corporate environments
- **Tool Permissions**: Pre-configured permissions for all Claude Code tools

## Quick Start

### 1. Set up API Key

```bash
# Set your Anthropic API key in Cubbi configuration
cubbi config set services.anthropic.api_key "your-api-key-here"
```

### 2. Run Claude Code Environment

```bash
# Start Claude Code container
cubbi run claudecode

# Execute Claude Code commands
cubbi exec claudecode "claude 'help me write a Python function'"

# Start interactive session
cubbi exec claudecode "claude"
```

## Configuration

### Required Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)

### Optional Environment Variables

- `ANTHROPIC_AUTH_TOKEN`: Custom authorization token for enterprise deployments
- `ANTHROPIC_CUSTOM_HEADERS`: Additional HTTP headers (JSON format)
- `CLAUDE_CODE_USE_BEDROCK`: Set to "true" to use Amazon Bedrock
- `CLAUDE_CODE_USE_VERTEX`: Set to "true" to use Google Vertex AI
- `HTTP_PROXY`: HTTP proxy server URL
- `HTTPS_PROXY`: HTTPS proxy server URL
- `DISABLE_TELEMETRY`: Set to "true" to disable telemetry

### Advanced Configuration

```bash
# Enterprise deployment with Bedrock
cubbi config set environment.claude_code_use_bedrock true
cubbi run claudecode

# With custom proxy
cubbi config set network.https_proxy "https://proxy.company.com:8080"
cubbi run claudecode

# Disable telemetry
cubbi config set environment.disable_telemetry true
cubbi run claudecode
```

## Usage Examples

### Basic Usage

```bash
# Get help
cubbi exec claudecode "claude --help"

# One-time task
cubbi exec claudecode "claude 'write a unit test for this function'"

# Interactive mode
cubbi exec claudecode "claude"
```

### Working with Projects

```bash
# Start Claude Code in your project directory
cubbi run claudecode --mount /path/to/your/project:/app
cubbi exec claudecode "cd /app && claude"

# Create a commit
cubbi exec claudecode "cd /app && claude commit"
```

### Advanced Features

```bash
# Run with specific model configuration
cubbi exec claudecode "claude -m claude-3-5-sonnet-20241022 'analyze this code'"

# Use with plan mode
cubbi exec claudecode "claude -p 'refactor this function'"
```

## Persistent Configuration

The following directories are automatically persisted:

- `~/.claude/`: Claude Code settings and configuration
- `~/.cache/claude/`: Claude Code cache and temporary files

Configuration files are maintained across container restarts, ensuring your settings and preferences are preserved.

## File Structure

```
cubbi/images/claudecode/
├── Dockerfile              # Container image definition
├── cubbi_image.yaml        # Cubbi image configuration
├── claudecode_plugin.py    # Authentication and setup plugin
├── cubbi_init.py          # Initialization script (shared)
├── init-status.sh         # Status check script (shared)
└── README.md              # This documentation
```

## Authentication Flow

1. **Environment Variables**: API key passed from Cubbi configuration
2. **Plugin Setup**: `claudecode_plugin.py` creates `~/.claude/settings.json`
3. **Verification**: Plugin verifies Claude Code installation and configuration
4. **Ready**: Claude Code is ready for use with configured authentication

## Troubleshooting

### Common Issues

**API Key Not Set**
```
⚠️ No authentication configuration found
Please set ANTHROPIC_API_KEY environment variable
```
**Solution**: Set API key in Cubbi configuration:
```bash
cubbi config set services.anthropic.api_key "your-api-key-here"
```

**Claude Code Not Found**
```
❌ Claude Code not properly installed
```
**Solution**: Rebuild the container image:
```bash
docker build -t cubbi-claudecode:latest cubbi/images/claudecode/
```

**Network Issues**
```
Connection timeout or proxy errors
```
**Solution**: Configure proxy settings:
```bash
cubbi config set network.https_proxy "your-proxy-url"
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Check configuration
cubbi exec claudecode "cat ~/.claude/settings.json"

# Verify installation
cubbi exec claudecode "claude --version"
cubbi exec claudecode "which claude"
cubbi exec claudecode "node --version"
```

## Security Considerations

- **API Keys**: Stored securely with 0o600 permissions
- **Configuration**: Settings files have restricted access
- **Environment**: Isolated container environment
- **Telemetry**: Can be disabled for privacy

## Development

### Building the Image

```bash
# Build locally
docker build -t cubbi-claudecode:test cubbi/images/claudecode/

# Test basic functionality
docker run --rm -it \
  -e ANTHROPIC_API_KEY="your-api-key" \
  cubbi-claudecode:test \
  bash -c "claude --version"
```

### Testing

```bash
# Run through Cubbi
cubbi run claudecode --name test-claude
cubbi exec test-claude "claude --version"
cubbi stop test-claude
```

## Support

For issues related to:
- **Cubbi Integration**: Check Cubbi documentation or open an issue
- **Claude Code**: Visit [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code)
- **API Keys**: Visit [Anthropic Console](https://console.anthropic.com/)

## License

This image configuration is provided under the same license as the Cubbi project. Claude Code is licensed separately by Anthropic.