# MCP Server Specification

## Overview

This document specifies the implementation for Model Control Protocol (MCP) server support in the Monadical Container (MC) system. The MCP server feature allows users to connect, build, and manage external MCP servers that can be attached to MC sessions.

An MCP server is a local (stdio) or remote (HTTP SSE server) service that can be accessed by a driver (such as Goose or Claude Code) to extend the LLM's capabilities through tool calls.

## Key Features

1. Support multiple types of MCP servers:
   - Remote HTTP SSE servers
   - Local container-based servers
   - Local container with MCP proxy for stdio-to-SSE conversion

2. Persistent MCP containers that can be:
   - Started/stopped independently of sessions
   - Connected to multiple sessions
   - Automatically started when referenced in a session creation

3. Management of MCP server configurations and containers

## MCP Configuration Model

The MCP configuration will be stored in the user configuration file and will include:

```yaml
mcps:
  - name: github
    type: docker
    image: mcp/github
    command: "github-mcp"
    env:
      - GITHUB_TOKEN: "your-token-here"

  - name: proxy-example
    type: proxy
    base_image: ghcr.io/mcp/github:latest
    proxy_image: ghcr.io/sparfenyuk/mcp-proxy:latest
    command: "github-mcp"
    proxy_options:
      sse_port: 8080
      sse_host: "0.0.0.0"
      allow_origin: "*"
    env:
      - GITHUB_TOKEN: "your-token-here"

  - name: remote-mcp
    type: remote
    url: "http://mcp-server.example.com/sse"
    headers:
      - Authorization: "Bearer your-token-here"
```

## CLI Commands

### MCP Management

```
mc mcp list                 # List all configured MCP servers and their status
mc mcp status <name>        # Show detailed status of a specific MCP server
mc mcp start <name>         # Start an MCP server container
mc mcp stop <name>          # Stop an MCP server container
mc mcp restart <name>       # Restart an MCP server container
mc mcp logs <name>          # Show logs for an MCP server container
```

### MCP Configuration

```
mc mcp remote add <name> <url> [--header KEY=VALUE...]  # Add a remote MCP server
mc mcp docker add <name> <image> [--command CMD] [--env KEY=VALUE...]  # Add a Docker-based MCP
mc mcp proxy add <name> <base_image> [--proxy-image IMG] [--command CMD] [--sse-port PORT] [--sse-host HOST] [--allow-origin ORIGIN] [--env KEY=VALUE...]  # Add a proxied MCP
mc mcp remove <name>  # Remove an MCP configuration
```

### Session Integration

```
mc session create [--mcp <name>]  # Create a session with an MCP server attached
```

## Implementation Details

### MCP Container Management

1. MCP containers will have their own dedicated Docker network
2. Session containers will be attached to both their session network and the MCP network when using an MCP
3. MCP containers will be persistent across sessions unless explicitly stopped
4. MCP containers will be named with a prefix to identify them (`mc_mcp_<name>`)

### Docker-based MCP Servers

For Docker-based MCP servers:
1. Pull the specified image
2. Create a dedicated network if it doesn't exist
3. Run the container with the specified environment variables and command

### Proxy-based MCP Servers

For proxy-based MCP servers:
1. Create a custom Dockerfile that:
   - Uses the specified proxy image as the base
   - Installs Docker-in-Docker capabilities
   - Sets up the base MCP server image
   - Configures the entrypoint to run the MCP proxy with the right parameters
2. Build the custom image
3. Run the container with the appropriate environment variables

### Remote MCP Servers

For remote MCP servers:
1. Store the URL and headers
2. Provide these to the session container when connecting

## Session Integration

When a session is created with an MCP server:
1. If the MCP server is not running, start it automatically
2. Connect the session container to the MCP server's network
3. Set the appropriate environment variables in the session to enable MCP connectivity

## Security Considerations

1. MCP server credentials and tokens should be handled securely through environment variables
2. Network isolation should be maintained between different MCP servers
3. Consider options for access control between sessions and MCP servers

## Future Enhancements

1. Support for MCP server version management
2. Health checking and automatic restart capabilities
3. Support for MCP server clusters or load balancing
4. Integration with monitoring systems