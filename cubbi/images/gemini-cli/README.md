# Google Gemini CLI for Cubbi

This image provides Google Gemini CLI in a Cubbi container environment.

## Overview

Google Gemini CLI is an AI-powered development tool that allows you to query and edit large codebases, generate applications from PDFs/sketches, automate operational tasks, and integrate with media generation tools using Google's Gemini models.

## Features

- **Advanced AI Models**: Access to Gemini 1.5 Pro, Flash, and other Google AI models
- **Codebase Analysis**: Query and edit large codebases intelligently
- **Multi-modal Support**: Work with text, images, PDFs, and sketches
- **Google Search Grounding**: Ground queries using Google Search for up-to-date information
- **Secure Authentication**: API key management through Cubbi's secure environment system
- **Persistent Configuration**: Settings and history preserved across container restarts
- **Project Integration**: Seamless integration with existing projects

## Quick Start

### 1. Set up API Key

```bash
# For Google AI (recommended)
uv run -m cubbi.cli config set services.google.api_key "your-gemini-api-key"

# Alternative using GEMINI_API_KEY
uv run -m cubbi.cli config set services.gemini.api_key "your-gemini-api-key"
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 2. Run Gemini CLI Environment

```bash
# Start Gemini CLI container with your project
uv run -m cubbi.cli session create --image gemini-cli /path/to/your/project

# Or without a project
uv run -m cubbi.cli session create --image gemini-cli
```

### 3. Use Gemini CLI

```bash
# Basic usage
gemini

# Interactive mode with specific query
gemini
> Write me a Discord bot that answers questions using a FAQ.md file

# Analyze existing project
gemini
> Give me a summary of all changes that went in yesterday

# Generate from sketch/PDF
gemini
> Create a web app based on this wireframe.png
```

## Configuration

### Supported API Keys

- `GEMINI_API_KEY`: Google AI API key for Gemini models
- `GOOGLE_API_KEY`: Alternative Google API key (compatibility)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Cloud service account JSON file

### Model Configuration

- `GEMINI_MODEL`: Default model (default: "gemini-1.5-pro")
  - Available: "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"
- `GEMINI_TEMPERATURE`: Model temperature 0.0-2.0 (default: 0.7)
- `GEMINI_MAX_TOKENS`: Maximum tokens in response

### Advanced Configuration

- `GEMINI_SEARCH_ENABLED`: Enable Google Search grounding (true/false, default: false)
- `GEMINI_DEBUG`: Enable debug mode (true/false, default: false)
- `GCLOUD_PROJECT`: Google Cloud project ID

### Network Configuration

- `HTTP_PROXY`: HTTP proxy server URL
- `HTTPS_PROXY`: HTTPS proxy server URL

## Usage Examples

### Basic AI Development

```bash
# Start Gemini CLI with your project
uv run -m cubbi.cli session create --image gemini-cli /path/to/project

# Inside the container:
gemini                               # Start interactive session
```

### Codebase Analysis

```bash
# Analyze changes
gemini
> What are the main functions in src/main.py?

# Code generation
gemini
> Add error handling to the authentication module

# Documentation
gemini
> Generate README documentation for this project
```

### Multi-modal Development

```bash
# Work with images
gemini
> Analyze this architecture diagram and suggest improvements

# PDF processing
gemini
> Convert this API specification PDF to OpenAPI YAML

# Sketch to code
gemini
> Create a React component based on this UI mockup
```

### Advanced Features

```bash
# With Google Search grounding
uv run -m cubbi.cli session create --image gemini-cli \
  --env GEMINI_SEARCH_ENABLED="true" \
  /path/to/project

# With specific model
uv run -m cubbi.cli session create --image gemini-cli \
  --env GEMINI_MODEL="gemini-1.5-flash" \
  --env GEMINI_TEMPERATURE="0.3" \
  /path/to/project

# Debug mode
uv run -m cubbi.cli session create --image gemini-cli \
  --env GEMINI_DEBUG="true" \
  /path/to/project
```

### Enterprise/Proxy Setup

```bash
# With proxy
uv run -m cubbi.cli session create --image gemini-cli \
  --env HTTPS_PROXY="https://proxy.company.com:8080" \
  /path/to/project

# With Google Cloud authentication
uv run -m cubbi.cli session create --image gemini-cli \
  --env GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json" \
  --env GCLOUD_PROJECT="your-project-id" \
  /path/to/project
```

## Persistent Configuration

The following directories are automatically persisted:

- `~/.config/gemini/`: Gemini CLI configuration files
- `~/.cache/gemini/`: Model cache and temporary files

Configuration files are maintained across container restarts, ensuring your preferences and session history are preserved.

## Model Recommendations

### Best Overall Performance
- **Gemini 1.5 Pro**: Excellent reasoning and code understanding
- **Gemini 1.5 Flash**: Faster responses, good for iterative development

### Cost-Effective Options
- **Gemini 1.5 Flash**: Lower cost, high speed
- **Gemini 1.0 Pro**: Basic model for simple tasks

### Specialized Use Cases
- **Code Analysis**: Gemini 1.5 Pro
- **Quick Iterations**: Gemini 1.5 Flash
- **Multi-modal Tasks**: Gemini 1.5 Pro (supports images, PDFs)

## File Structure

```
cubbi/images/gemini-cli/
├── Dockerfile              # Container image definition
├── cubbi_image.yaml        # Cubbi image configuration
├── gemini_plugin.py        # Authentication and setup plugin
└── README.md              # This documentation
```

## Authentication Flow

1. **API Key Setup**: API key configured via Cubbi configuration or environment variables
2. **Plugin Initialization**: `gemini_plugin.py` creates configuration files
3. **Environment File**: Creates `~/.config/gemini/.env` with API key
4. **Configuration**: Creates `~/.config/gemini/config.json` with settings
5. **Ready**: Gemini CLI is ready for use with configured authentication

## Troubleshooting

### Common Issues

**No API Key Found**
```
ℹ️ No API key found - Gemini CLI will require authentication
```
**Solution**: Set API key in Cubbi configuration:
```bash
uv run -m cubbi.cli config set services.google.api_key "your-key"
```

**Authentication Failed**
```
Error: Invalid API key or authentication failed
```
**Solution**: Verify your API key at [Google AI Studio](https://aistudio.google.com/apikey):
```bash
# Test your API key
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"
```

**Model Not Available**
```
Error: Model 'xyz' not found
```
**Solution**: Use supported models:
```bash
# List available models (inside container)
curl -H "Content-Type: application/json" \
     "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_API_KEY"
```

**Rate Limit Exceeded**
```
Error: Quota exceeded
```
**Solution**: Google AI provides:
- 60 requests per minute
- 1,000 requests per day
- Consider upgrading to Google Cloud for higher limits

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
# Enable debug output
uv run -m cubbi.cli session create --image gemini-cli \
  --env GEMINI_DEBUG="true"

# Check configuration
cat ~/.config/gemini/config.json

# Check environment
cat ~/.config/gemini/.env

# Test CLI directly
gemini --help
```

## Security Considerations

- **API Keys**: Stored securely with 0o600 permissions
- **Environment**: Isolated container environment
- **Configuration**: Secure file permissions for config files
- **Google Cloud**: Supports service account authentication for enterprise use

## Advanced Configuration

### Custom Model Configuration

```bash
# Use specific model with custom settings
uv run -m cubbi.cli session create --image gemini-cli \
  --env GEMINI_MODEL="gemini-1.5-flash" \
  --env GEMINI_TEMPERATURE="0.2" \
  --env GEMINI_MAX_TOKENS="8192"
```

### Google Search Integration

```bash
# Enable Google Search grounding for up-to-date information
uv run -m cubbi.cli session create --image gemini-cli \
  --env GEMINI_SEARCH_ENABLED="true"
```

### Google Cloud Integration

```bash
# Use with Google Cloud service account
uv run -m cubbi.cli session create --image gemini-cli \
  --env GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json" \
  --env GCLOUD_PROJECT="your-project-id"
```

## API Limits and Pricing

### Free Tier (Google AI)
- 60 requests per minute
- 1,000 requests per day
- Personal Google account required

### Paid Tier (Google Cloud)
- Higher rate limits
- Enterprise features
- Service account authentication
- Custom quotas available

## Support

For issues related to:
- **Cubbi Integration**: Check Cubbi documentation or open an issue
- **Gemini CLI Functionality**: Visit [Gemini CLI documentation](https://github.com/google-gemini/gemini-cli)
- **Google AI Platform**: Visit [Google AI documentation](https://ai.google.dev/)
- **API Keys**: Visit [Google AI Studio](https://aistudio.google.com/)

## License

This image configuration is provided under the same license as the Cubbi project. Google Gemini CLI is licensed separately by Google.