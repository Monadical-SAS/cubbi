# MCP Server Specification

## Overview

This document specifies the implementation for Model Control Protocol (MCP) server support in the Monadical Container (MC) system. The MCP server feature allows users to connect, build, and manage external MCP servers that can be attached to MC sessions.

An MCP server is a service that can be accessed by a driver (such as Goose or Claude Code) to extend the LLM's capabilities through tool calls. It can be either:
- A local stdio-based MCP server running in a container (accessed via an SSE proxy)
- A remote HTTP SSE server accessed directly via its URL

## Key Features

1. Support two types of MCP servers:
   - **Proxy-based MCP servers** (default): Container running an MCP stdio server with a proxy that converts to SSE
   - **Remote MCP servers**: External HTTP SSE servers accessed via URL

2. Persistent MCP containers that can be:
   - Started/stopped independently of sessions
   - Connected to multiple sessions
   - Automatically started when referenced in a session creation

3. Management of MCP server configurations and containers

## MCP Configuration Model

The MCP configuration will be stored in the user configuration file and will include:

```yaml
mcps:
  # Proxy-based MCP server (default type)
  - name: github
    type: proxy
    base_image: mcp/github
    command: "github-mcp"  # Optional command to run in the base image
    proxy_image: ghcr.io/sparfenyuk/mcp-proxy:latest  # Optional, defaults to standard proxy image
    proxy_options:
      sse_port: 8080
      sse_host: "0.0.0.0"
      allow_origin: "*"
    env:
      GITHUB_TOKEN: "your-token-here"

  # Remote MCP server
  - name: remote-mcp
    type: remote
    url: "http://mcp-server.example.com/sse"
    headers:
      Authorization: "Bearer your-token-here"
```

## CLI Commands

### MCP Management

```
mc mcp list                # List all configured MCP servers and their status
mc mcp status <name>          # Show detailed status of a specific MCP server
mc mcp start <name>           # Start an MCP server container
mc mcp stop <name>            # Stop and remove an MCP server container
mc mcp restart <name>         # Restart an MCP server container
mc mcp start --all         # Start all MCP server containers
mc mcp stop --all          # Stop and remove all MCP server containers
mc mcp inspector                      # Run the MCP Inspector UI with network connectivity to all MCP servers
mc mcp inspector --client-port <cp> --server-port <sp>  # Run with custom client port (default: 5173) and server port (default: 3000)
mc mcp inspector --detach  # Run the inspector in detached mode
mc mcp inspector --stop    # Stop the running inspector
mc mcp logs <name>            # Show logs for an MCP server container
```

### MCP Configuration

```
# Add a proxy-based MCP server (default)
mc mcp add <name> <base_image> [--command CMD] [--proxy-image IMG] [--sse-port PORT] [--sse-host HOST] [--allow-origin ORIGIN] [--env KEY=VALUE...]

# Add a remote MCP server
mc mcp add-remote <name> <url> [--header KEY=VALUE...]

# Remove an MCP configuration
mc mcp remove <name>
```

### Session Integration

```
mc session create [--mcp <name>]  # Create a session with an MCP server attached
```

## Implementation Details

### MCP Container Management

1. MCP containers will have their own dedicated Docker network (`mc-mcp-network`)
2. Session containers will be attached to both their session network and the MCP network when using an MCP
3. MCP containers will be persistent across sessions unless explicitly stopped
4. MCP containers will be named with a prefix to identify them (`mc_mcp_<name>`)
5. Each MCP container will have a network alias matching its name without the prefix (e.g., `mc_mcp_github` will have the alias `github`)
6. Network aliases enable DNS-based service discovery between containers

### MCP Inspector

The MCP Inspector is a web-based UI tool that allows you to:

1. Visualize and interact with multiple MCP servers
2. Debug MCP server messages and interactions
3. Test MCP server capabilities directly

The MCP Inspector implementation includes:

1. A container based on the `mcp/inspector` image
2. Automatic joining of all MCP server networks for seamless DNS resolution
3. A modified Express server that binds to all interfaces (0.0.0.0)
4. Port mapping for both the frontend (default: 5173) and backend API (default: 3000)
5. Network connectivity to all MCP servers using their simple names as DNS hostnames

### Proxy-based MCP Servers (Default)

For proxy-based MCP servers:
1. Create a custom Dockerfile that:
   - Uses the specified proxy image as the base
   - Installs Docker-in-Docker capabilities
   - Sets up the base MCP server image
   - Configures the entrypoint to run the MCP proxy with the right parameters
2. Build the custom image
3. Run the container with:
   - The Docker socket mounted to enable Docker-in-Docker
   - Environment variables from the configuration
   - The SSE server port exposed

The proxy container will:
1. Pull the base image
2. Run the base image with the specified command
3. Connect the stdio of the base image to the MCP proxy
4. Expose an SSE server that clients can connect to

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