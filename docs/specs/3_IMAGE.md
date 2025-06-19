# Cubbi Image Specifications

## Overview

This document defines the specifications and requirements for building Cubbi-compatible container images. These images serve as isolated development environments for AI tools within the Cubbi platform.

## Architecture

Cubbi images use a Python-based initialization system with a plugin architecture that separates core Cubbi functionality from tool-specific configuration.

### Core Components

1. **Image Metadata File** (`cubbi_image.yaml`) - *Tool-specific*
2. **Container Definition** (`Dockerfile`) - *Tool-specific*
3. **Python Initialization Script** (`cubbi_init.py`) - *Shared across all images*
4. **Tool-specific Plugins** (e.g., `goose_plugin.py`) - *Tool-specific*
5. **Status Tracking Scripts** (`init-status.sh`) - *Shared across all images*

## Image Metadata Specification

### Required Fields

```yaml
name: string               # Unique identifier for the image
description: string        # Human-readable description
version: string           # Semantic version (e.g., "1.0.0")
maintainer: string        # Contact information
image: string             # Docker image name and tag
```

### Environment Variables

```yaml
environment:
  - name: string          # Variable name
    description: string   # Human-readable description
    required: boolean     # Whether variable is mandatory
    sensitive: boolean    # Whether variable contains secrets
    default: string       # Default value (optional)
```

#### Standard Environment Variables

All images MUST support these standard environment variables:

- `CUBBI_USER_ID`: UID for the container user (default: 1000)
- `CUBBI_GROUP_ID`: GID for the container user (default: 1000)
- `CUBBI_RUN_COMMAND`: Command to execute after initialization
- `CUBBI_NO_SHELL`: Exit after command execution ("true"/"false")
- `CUBBI_CONFIG_DIR`: Directory for persistent configurations (default: "/cubbi-config")
- `CUBBI_MODEL`: Model to use for the tool
- `CUBBI_PROVIDER`: Provider to use for the tool

#### MCP Integration Variables

For MCP (Model Context Protocol) integration:

- `MCP_COUNT`: Number of available MCP servers
- `MCP_{idx}_NAME`: Name of MCP server at index
- `MCP_{idx}_TYPE`: Type of MCP server
- `MCP_{idx}_HOST`: Hostname of MCP server
- `MCP_{idx}_URL`: Full URL for remote MCP servers

### Network Configuration

```yaml
ports:
  - number              # Port to expose (e.g., 8000)
```

### Storage Configuration

```yaml
volumes:
  - mountPath: string   # Path inside container
    description: string # Purpose of the volume

persistent_configs:
  - source: string      # Path inside container
    target: string      # Path in persistent storage
    type: string        # "file" or "directory"
    description: string # Purpose of the configuration
```

## Container Requirements

### Base System Dependencies

All images MUST include:

- `python3` - For the initialization system
- `gosu` - For secure user switching
- `bash` - For script execution

### Python Dependencies

The Cubbi initialization system requires:

- `ruamel.yaml` - For YAML configuration parsing

### User Management

Images MUST:

1. Run as root initially for setup
2. Create a non-root user (`cubbi`) with configurable UID/GID
3. Switch to the non-root user for tool execution
4. Handle user ID mapping for volume permissions

### Directory Structure

Standard directories:

- `/app` - Primary working directory (owned by cubbi user)
- `/home/cubbi` - User home directory
- `/cubbi-config` - Persistent configuration storage
- `/cubbi/init.log` - Initialization log file
- `/cubbi/init.status` - Initialization status tracking
- `/cubbi/cubbi_image.yaml` - Image configuration

## Initialization System

### Shared Scripts

The following scripts are **shared across all Cubbi images** and should be copied from the main Cubbi repository:

#### Main Script (`cubbi_init.py`) - *Shared*

The standalone initialization script that:

1. Sets up user and group with proper IDs
2. Creates standard directories with correct permissions
3. Sets up persistent configuration symlinks
4. Runs tool-specific initialization
5. Executes user commands or starts interactive shell

The script supports:
- `--help` for usage information
- Argument passing to final command
- Environment variable configuration
- Plugin-based tool initialization

#### Status Tracking Script (`init-status.sh`) - *Shared*

A bash script that:
- Monitors initialization progress
- Displays logs during setup
- Ensures files exist before operations
- Switches to user shell when complete

### Tool-Specific Components

#### Tool Plugins (`{tool}_plugin.py`) - *Tool-specific*

Each tool MUST provide a plugin (`{tool}_plugin.py`) implementing:

```python
from cubbi_init import ToolPlugin

class MyToolPlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "mytool"

    def initialize(self) -> bool:
        """Main tool initialization logic"""
        # Tool-specific setup
        return True

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate with available MCP servers"""
        # MCP integration logic
        return True
```

#### Image Configuration (`cubbi_image.yaml`) - *Tool-specific*

Each tool provides its own metadata file defining:
- Tool-specific environment variables
- Port configurations
- Volume mounts
- Persistent configuration mappings

## Plugin Architecture

### Plugin Discovery

Plugins are automatically discovered by:

1. Looking for `{image_name}_plugin.py` in the same directory as `cubbi_init.py`
2. Loading classes that inherit from `ToolPlugin`
3. Executing initialization and MCP integration

### Plugin Requirements

Tool plugins MUST:
- Inherit from `ToolPlugin` base class
- Implement `tool_name` property
- Implement `initialize()` method
- Optionally implement `integrate_mcp_servers()` method
- Use ruamel.yaml for configuration file operations

## Security Requirements

### User Isolation

- Container MUST NOT run processes as root after initialization
- All user processes MUST run as the `cubbi` user
- Proper file ownership and permissions MUST be maintained

### Secrets Management

- Sensitive environment variables MUST be marked as `sensitive: true`
- SSH keys and tokens MUST have restricted permissions (600)
- No secrets SHOULD be logged or exposed in configuration files

### Network Security

- Only necessary ports SHOULD be exposed
- Network services should be properly configured and secured

## Integration Requirements

### MCP Server Integration

Images MUST support dynamic MCP server discovery and configuration through:

1. Environment variable parsing for server count and details
2. Automatic tool configuration updates
3. Standard MCP communication protocols

### Persistent Configuration

Images MUST support:

1. Configuration persistence through volume mounts
2. Symlink creation for tool configuration directories
3. Proper ownership and permission handling

## Docker Integration

### Dockerfile Requirements

```dockerfile
# Copy shared scripts from main Cubbi repository
COPY cubbi_init.py /cubbi_init.py                    # Shared
COPY init-status.sh /init-status.sh                  # Shared

# Copy tool-specific files
COPY {tool}_plugin.py /{tool}_plugin.py              # Tool-specific
COPY cubbi_image.yaml /cubbi/cubbi_image.yaml        # Tool-specific

# Install Python dependencies
RUN pip install ruamel.yaml

# Make scripts executable
RUN chmod +x /cubbi_init.py /init-status.sh

# Set entrypoint
ENTRYPOINT ["/cubbi_init.py"]
CMD ["tail", "-f", "/dev/null"]
```

### Init Container Support

For complex initialization, use:

```dockerfile
# Use init-status.sh as entrypoint for monitoring
ENTRYPOINT ["/init-status.sh"]
```

## Best Practices

### Performance

- Use multi-stage builds to minimize image size
- Clean up package caches and temporary files
- Use specific base image versions for reproducibility

### Maintainability

- Follow consistent naming conventions
- Include comprehensive documentation
- Use semantic versioning for image releases
- Provide clear error messages and logging

### Compatibility

- Support common development workflows
- Maintain backward compatibility when possible
- Test with various project types and configurations

## Validation Checklist

Before releasing a Cubbi image, verify:

- [ ] All required metadata fields are present in `cubbi_image.yaml`
- [ ] Standard environment variables are supported
- [ ] `cubbi_init.py` script is properly installed and executable
- [ ] Tool plugin is discovered and loads correctly
- [ ] User management works correctly
- [ ] Persistent configurations are properly handled
- [ ] MCP integration functions (if applicable)
- [ ] Tool-specific functionality works as expected
- [ ] Security requirements are met
- [ ] Python dependencies are satisfied
- [ ] Status tracking works correctly
- [ ] Documentation is complete and accurate

## Examples

### Complete Goose Example

See the `/cubbi/images/goose/` directory for a complete implementation including:
- `Dockerfile` - Container definition
- `cubbi_image.yaml` - Image metadata
- `goose_plugin.py` - Tool-specific initialization
- `README.md` - Tool-specific documentation

### Migration Notes

The current Python-based system uses:
- `cubbi_init.py` - Standalone initialization script with plugin support
- `{tool}_plugin.py` - Tool-specific configuration and MCP integration
- `init-status.sh` - Status monitoring and log display
- `cubbi_image.yaml` - Image metadata and configuration
