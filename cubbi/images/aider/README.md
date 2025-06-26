# Aider for Cubbi

This image provides Aider (AI pair programming) in a Cubbi container environment.

## Overview

Aider is an AI pair programming tool that works in your terminal. This Cubbi image integrates Aider with secure API key management, persistent configuration, and support for multiple LLM providers.

## Features

- **Multiple LLM Support**: Works with OpenAI, Anthropic, DeepSeek, Gemini, OpenRouter, and more
- **Secure Authentication**: API key management through Cubbi's secure environment system
- **Persistent Configuration**: Settings and history preserved across container restarts
- **Git Integration**: Automatic commits and git awareness
- **Multi-Language Support**: Works with 100+ programming languages

## Quick Start

### 1. Set up API Key

```bash
# For OpenAI (GPT models)
uv run -m cubbi.cli config set services.openai.api_key "your-openai-key"

# For Anthropic (Claude models)
uv run -m cubbi.cli config set services.anthropic.api_key "your-anthropic-key"

# For DeepSeek (recommended for cost-effectiveness)
uv run -m cubbi.cli config set services.deepseek.api_key "your-deepseek-key"
```

### 2. Run Aider Environment

```bash
# Start Aider container with your project
uv run -m cubbi.cli session create --image aider /path/to/your/project

# Or without a project
uv run -m cubbi.cli session create --image aider
```

### 3. Use Aider

```bash
# Basic usage
aider

# With specific model
aider --model sonnet

# With specific files
aider main.py utils.py

# One-shot request
aider --message "Add error handling to the login function"
```

## Configuration

### Supported API Keys

- `OPENAI_API_KEY`: OpenAI GPT models (GPT-4, GPT-4o, etc.)
- `ANTHROPIC_API_KEY`: Anthropic Claude models (Sonnet, Haiku, etc.)
- `DEEPSEEK_API_KEY`: DeepSeek models (cost-effective option)
- `GEMINI_API_KEY`: Google Gemini models
- `OPENROUTER_API_KEY`: OpenRouter (access to many models)

### Additional Configuration

- `AIDER_MODEL`: Default model to use (e.g., "sonnet", "o3-mini", "deepseek")
- `AIDER_AUTO_COMMITS`: Enable automatic git commits (default: true)
- `AIDER_DARK_MODE`: Enable dark mode interface (default: false)
- `AIDER_API_KEYS`: Additional API keys in format "provider1=key1,provider2=key2"

### Network Configuration

- `HTTP_PROXY`: HTTP proxy server URL
- `HTTPS_PROXY`: HTTPS proxy server URL

## Usage Examples

### Basic AI Pair Programming

```bash
# Start Aider with your project
uv run -m cubbi.cli session create --image aider /path/to/project

# Inside the container:
aider                          # Start interactive session
aider main.py                  # Work on specific file
aider --message "Add tests"    # One-shot request
```

### Model Selection

```bash
# Use Claude Sonnet
aider --model sonnet

# Use GPT-4o
aider --model gpt-4o

# Use DeepSeek (cost-effective)
aider --model deepseek

# Use OpenRouter
aider --model openrouter/anthropic/claude-3.5-sonnet
```

### Advanced Features

```bash
# Work with multiple files
aider src/main.py tests/test_main.py

# Auto-commit changes
aider --auto-commits

# Read-only mode (won't edit files)
aider --read

# Apply a specific change
aider --message "Refactor the database connection code to use connection pooling"
```

### Enterprise/Proxy Setup

```bash
# With proxy
uv run -m cubbi.cli session create --image aider \
  --env HTTPS_PROXY="https://proxy.company.com:8080" \
  /path/to/project

# With custom model
uv run -m cubbi.cli session create --image aider \
  --env AIDER_MODEL="sonnet" \
  /path/to/project
```

## Persistent Configuration

The following directories are automatically persisted:

- `~/.aider/`: Aider configuration and chat history
- `~/.cache/aider/`: Model cache and temporary files

Configuration files are maintained across container restarts, ensuring your preferences and chat history are preserved.

## Model Recommendations

### Best Overall Performance
- **Claude 3.5 Sonnet**: Excellent code understanding and generation
- **OpenAI GPT-4o**: Strong performance across languages
- **Gemini 2.5 Pro**: Good balance of quality and speed

### Cost-Effective Options
- **DeepSeek V3**: Very cost-effective, good quality
- **OpenRouter**: Access to multiple models with competitive pricing

### Free Options
- **Gemini 2.5 Pro Exp**: Free tier available
- **OpenRouter**: Some free models available

## File Structure

```
cubbi/images/aider/
├── Dockerfile              # Container image definition
├── cubbi_image.yaml        # Cubbi image configuration
├── aider_plugin.py         # Authentication and setup plugin
└── README.md              # This documentation
```

## Authentication Flow

1. **Environment Variables**: API keys passed from Cubbi configuration
2. **Plugin Setup**: `aider_plugin.py` creates environment configuration
3. **Environment File**: Creates `~/.aider/.env` with API keys
4. **Ready**: Aider is ready for use with configured authentication

## Troubleshooting

### Common Issues

**No API Key Found**
```
ℹ️ No API keys found - Aider will run without pre-configuration
```
**Solution**: Set API key in Cubbi configuration:
```bash
uv run -m cubbi.cli config set services.openai.api_key "your-key"
```

**Model Not Available**
```
Error: Model 'xyz' not found
```
**Solution**: Check available models for your provider:
```bash
aider --models  # List available models
```

**Git Issues**
```
Git repository not found
```
**Solution**: Initialize git in your project or mount a git repository:
```bash
git init
# or
uv run -m cubbi.cli session create --image aider /path/to/git/project
```

**Network/Proxy Issues**
```
Connection timeout or proxy errors
```
**Solution**: Configure proxy settings:
```bash
uv run -m cubbi.cli config set network.https_proxy "your-proxy-url"
```

### Debug Mode

```bash
# Check Aider version
aider --version

# List available models
aider --models

# Check configuration
cat ~/.aider/.env

# Verbose output
aider --verbose
```

## Security Considerations

- **API Keys**: Stored securely with 0o600 permissions
- **Environment**: Isolated container environment
- **Git Integration**: Respects .gitignore and git configurations
- **Code Safety**: Always review changes before accepting

## Advanced Configuration

### Custom Model Configuration

```bash
# Use with custom API endpoint
uv run -m cubbi.cli session create --image aider \
  --env OPENAI_API_BASE="https://api.custom-provider.com/v1" \
  --env OPENAI_API_KEY="your-key"
```

### Multiple API Keys

```bash
# Configure multiple providers
uv run -m cubbi.cli session create --image aider \
  --env OPENAI_API_KEY="openai-key" \
  --env ANTHROPIC_API_KEY="anthropic-key" \
  --env AIDER_API_KEYS="provider1=key1,provider2=key2"
```

## Support

For issues related to:
- **Cubbi Integration**: Check Cubbi documentation or open an issue
- **Aider Functionality**: Visit [Aider documentation](https://aider.chat/)
- **Model Configuration**: Check [LLM documentation](https://aider.chat/docs/llms.html)
- **API Keys**: Visit provider documentation (OpenAI, Anthropic, etc.)

## License

This image configuration is provided under the same license as the Cubbi project. Aider is licensed separately under Apache 2.0.