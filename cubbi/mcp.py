"""
MCP (Model Control Protocol) server management for Cubbi Container.
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

import docker
from docker.errors import DockerException, ImageNotFound, NotFound

from .models import DockerMCP, MCPContainer, MCPStatus, ProxyMCP, RemoteMCP
from .user_config import UserConfigManager

# Configure logging
logger = logging.getLogger(__name__)


class MCPManager:
    """Manager for MCP (Model Control Protocol) servers."""

    def __init__(
        self,
        config_manager: Optional[UserConfigManager] = None,
    ):
        """Initialize the MCP manager."""
        self.config_manager = config_manager or UserConfigManager()
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
        except DockerException as e:
            logger.error(f"Error connecting to Docker: {e}")
            self.client = None

    def _ensure_mcp_network(self) -> str:
        """Ensure the MCP network exists and return its name.
        Note: This is used only by the inspector, not for session-to-MCP connections.
        """
        network_name = "cubbi-mcp-network"
        if self.client:
            networks = self.client.networks.list(names=[network_name])
            if not networks:
                self.client.networks.create(network_name, driver="bridge")
        return network_name

    def _get_mcp_dedicated_network(self, mcp_name: str) -> str:
        """Get or create a dedicated network for direct session-to-MCP connections.

        Args:
            mcp_name: The name of the MCP server

        Returns:
            The name of the dedicated network
        """
        network_name = f"cubbi-mcp-{mcp_name}-network"
        if self.client:
            networks = self.client.networks.list(names=[network_name])
            if not networks:
                self.client.networks.create(network_name, driver="bridge")
        return network_name

    def list_mcps(self) -> List[Dict[str, Any]]:
        """List all configured MCP servers."""
        mcps = self.config_manager.get("mcps", [])
        return mcps

    def get_mcp(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an MCP configuration by name."""
        mcps = self.list_mcps()
        for mcp in mcps:
            if mcp.get("name") == name:
                return mcp
        return None

    def add_remote_mcp(
        self,
        name: str,
        url: str,
        headers: Dict[str, str] = None,
        add_as_default: bool = True,
    ) -> Dict[str, Any]:
        """Add a remote MCP server.

        Args:
            name: Name of the MCP server
            url: URL of the remote MCP server
            headers: HTTP headers to use when connecting
            add_as_default: Whether to add this MCP to the default MCPs list

        Returns:
            The MCP configuration dictionary
        """
        # Create the remote MCP configuration
        remote_mcp = RemoteMCP(
            name=name,
            url=url,
            headers=headers or {},
        )

        # Add to the configuration
        mcps = self.list_mcps()

        # Remove existing MCP with the same name if it exists
        mcps = [mcp for mcp in mcps if mcp.get("name") != name]

        # Add the new MCP
        mcp_config = remote_mcp.model_dump()
        mcps.append(mcp_config)

        # Save the configuration
        self.config_manager.set("mcps", mcps)

        # Add to default MCPs if requested
        if add_as_default:
            default_mcps = self.config_manager.get("defaults.mcps", [])
            if name not in default_mcps:
                default_mcps.append(name)
                self.config_manager.set("defaults.mcps", default_mcps)

        return mcp_config

    def add_docker_mcp(
        self,
        name: str,
        image: str,
        command: str,
        env: Dict[str, str] = None,
        add_as_default: bool = True,
    ) -> Dict[str, Any]:
        """Add a Docker-based MCP server.

        Args:
            name: Name of the MCP server
            image: Docker image for the MCP server
            command: Command to run in the container
            env: Environment variables to set in the container
            add_as_default: Whether to add this MCP to the default MCPs list

        Returns:
            The MCP configuration dictionary
        """
        # Create the Docker MCP configuration
        docker_mcp = DockerMCP(
            name=name,
            image=image,
            command=command,
            env=env or {},
        )

        # Add to the configuration
        mcps = self.list_mcps()

        # Remove existing MCP with the same name if it exists
        mcps = [mcp for mcp in mcps if mcp.get("name") != name]

        # Add the new MCP
        mcp_config = docker_mcp.model_dump()
        mcps.append(mcp_config)

        # Save the configuration
        self.config_manager.set("mcps", mcps)

        # Add to default MCPs if requested
        if add_as_default:
            default_mcps = self.config_manager.get("defaults.mcps", [])
            if name not in default_mcps:
                default_mcps.append(name)
                self.config_manager.set("defaults.mcps", default_mcps)

        return mcp_config

    def add_proxy_mcp(
        self,
        name: str,
        base_image: str,
        proxy_image: str,
        command: str,
        proxy_options: Dict[str, Any] = None,
        env: Dict[str, str] = None,
        host_port: Optional[int] = None,
        add_as_default: bool = True,
    ) -> Dict[str, Any]:
        """Add a proxy-based MCP server.

        Args:
            name: Name of the MCP server
            base_image: Base Docker image running the actual MCP server
            proxy_image: Docker image for the MCP proxy
            command: Command to run in the container
            proxy_options: Options for the MCP proxy
            env: Environment variables to set in the container
            host_port: Host port to bind the MCP server to (auto-assigned if not specified)
            add_as_default: Whether to add this MCP to the default MCPs list

        Returns:
            The MCP configuration dictionary
        """
        # If no host port specified, find the next available port starting from 5101
        if host_port is None:
            # Get current MCPs and find highest assigned port
            mcps = self.list_mcps()
            highest_port = 5100  # Start at 5100, so next will be 5101

            for mcp in mcps:
                if mcp.get("type") == "proxy" and mcp.get("host_port"):
                    try:
                        port = int(mcp.get("host_port"))
                        if port > highest_port:
                            highest_port = port
                    except (ValueError, TypeError):
                        pass

            # Next port will be highest + 1
            host_port = highest_port + 1

        # Create the Proxy MCP configuration
        proxy_mcp = ProxyMCP(
            name=name,
            base_image=base_image,
            proxy_image=proxy_image,
            command=command,
            proxy_options=proxy_options or {},
            env=env or {},
            host_port=host_port,
        )

        # Add to the configuration
        mcps = self.list_mcps()

        # Remove existing MCP with the same name if it exists
        mcps = [mcp for mcp in mcps if mcp.get("name") != name]

        # Add the new MCP
        mcp_config = proxy_mcp.model_dump()
        mcps.append(mcp_config)

        # Save the configuration
        self.config_manager.set("mcps", mcps)

        # Add to default MCPs if requested
        if add_as_default:
            default_mcps = self.config_manager.get("defaults.mcps", [])
            if name not in default_mcps:
                default_mcps.append(name)
                self.config_manager.set("defaults.mcps", default_mcps)

        return mcp_config

    def remove_mcp(self, name: str) -> bool:
        """Remove an MCP server configuration.

        Args:
            name: Name of the MCP server to remove

        Returns:
            True if the MCP was successfully removed, False otherwise
        """
        mcps = self.list_mcps()

        # Filter out the MCP with the specified name
        updated_mcps = [mcp for mcp in mcps if mcp.get("name") != name]

        # If the length hasn't changed, the MCP wasn't found
        if len(mcps) == len(updated_mcps):
            return False

        # Save the updated configuration
        self.config_manager.set("mcps", updated_mcps)

        # Also remove from default MCPs if it's there
        default_mcps = self.config_manager.get("defaults.mcps", [])
        if name in default_mcps:
            default_mcps.remove(name)
            self.config_manager.set("defaults.mcps", default_mcps)

        # Stop and remove the container if it exists
        self.stop_mcp(name)

        return True

    def get_mcp_container_name(self, mcp_name: str) -> str:
        """Get the Docker container name for an MCP server."""
        return f"cubbi_mcp_{mcp_name}"

    def start_mcp(self, name: str) -> Dict[str, Any]:
        """Start an MCP server container."""
        if not self.client:
            raise Exception("Docker client is not available")

        # Get the MCP configuration
        mcp_config = self.get_mcp(name)
        if not mcp_config:
            raise ValueError(f"MCP server '{name}' not found")

        # Get the container name
        container_name = self.get_mcp_container_name(name)

        # Check if the container already exists
        try:
            container = self.client.containers.get(container_name)
            # Check if we need to recreate the container due to port binding changes
            needs_recreate = False

            if mcp_config.get("type") == "proxy" and mcp_config.get("host_port"):
                # Get the current container port bindings
                port_bindings = container.attrs.get("HostConfig", {}).get(
                    "PortBindings", {}
                )
                sse_port = f"{mcp_config['proxy_options'].get('sse_port', 8080)}/tcp"

                # Check if the port binding matches the configured host port
                current_binding = port_bindings.get(sse_port, [])
                if not current_binding or int(
                    current_binding[0].get("HostPort", 0)
                ) != mcp_config.get("host_port"):
                    logger.info(
                        f"Port binding changed for MCP '{name}', recreating container"
                    )
                    needs_recreate = True

            # If we don't need to recreate, just start it if it's not running
            if not needs_recreate:
                if container.status != "running":
                    container.start()

                # Return the container status
                return {
                    "container_id": container.id,
                    "status": "running",
                    "name": name,
                }
            else:
                # We need to recreate the container with new port bindings
                logger.info(
                    f"Recreating container for MCP '{name}' with updated port bindings"
                )
                container.remove(force=True)
                # Container doesn't exist, we need to create it
                pass
        except NotFound:
            # Container doesn't exist, we need to create it
            pass

        # Ensure the MCP network exists
        network_name = self._ensure_mcp_network()

        # Handle different MCP types
        mcp_type = mcp_config.get("type")

        if mcp_type == "remote":
            # Remote MCP servers don't need containers
            return {
                "status": "not_applicable",
                "name": name,
                "type": "remote",
            }

        elif mcp_type == "docker":
            # Pull the image if needed
            try:
                self.client.images.get(mcp_config["image"])
            except ImageNotFound:
                logger.info(f"Pulling image {mcp_config['image']}")
                self.client.images.pull(mcp_config["image"])

            # Create and start the container
            container = self.client.containers.run(
                image=mcp_config["image"],
                command=mcp_config.get("command"),
                name=container_name,
                detach=True,
                network=None,  # Start without network, we'll add it with aliases
                environment=mcp_config.get("env", {}),
                labels={
                    "cubbi.mcp": "true",
                    "cubbi.mcp.name": name,
                    "cubbi.mcp.type": "docker",
                },
            )

            # Connect to the inspector network
            network = self.client.networks.get(network_name)
            network.connect(container, aliases=[name])
            logger.info(
                f"Connected MCP server '{name}' to inspector network {network_name} with alias '{name}'"
            )

            # Create and connect to a dedicated network for session connections
            dedicated_network_name = self._get_mcp_dedicated_network(name)
            try:
                dedicated_network = self.client.networks.get(dedicated_network_name)
            except DockerException:
                dedicated_network = self.client.networks.create(
                    dedicated_network_name, driver="bridge"
                )

            dedicated_network.connect(container, aliases=[name])
            logger.info(
                f"Connected MCP server '{name}' to dedicated network {dedicated_network_name} with alias '{name}'"
            )

            return {
                "container_id": container.id,
                "status": "running",
                "name": name,
            }

        elif mcp_type == "proxy":
            # For proxy, we need to create a custom Dockerfile and build an image
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create entrypoint script for mcp-proxy that runs the base MCP image
                entrypoint_script = """#!/bin/sh
set -x
echo "Starting MCP proxy with base image $MCP_BASE_IMAGE (command: $MCP_COMMAND) on port $SSE_PORT"

# Verify if Docker socket is available
if [ ! -S /var/run/docker.sock ]; then
    echo "ERROR: Docker socket not available. Cannot run base MCP image."
    echo "Make sure the Docker socket is mounted from the host."

    # Create a minimal fallback server for testing
    cat > /tmp/fallback_server.py << 'EOF'
import json, sys, time
print(json.dumps({"type": "ready", "message": "Fallback server - Docker socket not available"}))
sys.stdout.flush()
while True:
    line = sys.stdin.readline().strip()
    if line:
        try:
            data = json.loads(line)
            if data.get("type") == "ping":
                print(json.dumps({"type": "pong", "id": data.get("id")}))
            else:
                print(json.dumps({"type": "error", "message": "Docker socket not available"}))
        except:
            print(json.dumps({"type": "error"}))
        sys.stdout.flush()
    time.sleep(1)
EOF

    exec mcp-proxy \
      --sse-port "$SSE_PORT" \
      --sse-host "$SSE_HOST" \
      --allow-origin "$ALLOW_ORIGIN" \
      --pass-environment \
      -- \
      python /tmp/fallback_server.py
    exit 1
fi

# Pull the base MCP image
echo "Pulling base MCP image: $MCP_BASE_IMAGE"
docker pull "$MCP_BASE_IMAGE" || true

# Prepare the command to run the MCP server
if [ -n "$MCP_COMMAND" ]; then
    CMD="$MCP_COMMAND"
else
    # Default to empty if no command specified
    CMD=""
fi

echo "Running MCP server from image $MCP_BASE_IMAGE with command: $CMD"

# Run the actual MCP server in the base image and pipe its I/O to mcp-proxy
# Using docker run without -d to keep stdio connected

# Build env vars string to pass through to the inner container
ENV_ARGS=""

# Check if the environment variable names file exists
if [ -f "/mcp-envs.txt" ]; then
  # Read env var names from file and pass them to docker
  while read -r var_name; do
    # Skip empty lines
    if [ -n "$var_name" ]; then
      # Simply add the env var - Docker will only pass it if it exists
      ENV_ARGS="$ENV_ARGS -e $var_name"
    fi
  done < "/mcp-envs.txt"

  echo "Passing environment variables from mcp-envs.txt: $ENV_ARGS"
fi

exec mcp-proxy \
  --sse-port "$SSE_PORT" \
  --sse-host "$SSE_HOST" \
  --allow-origin "$ALLOW_ORIGIN" \
  --pass-environment \
  -- \
  docker run --rm -i $ENV_ARGS "$MCP_BASE_IMAGE" $CMD
"""
                # Write the entrypoint script
                entrypoint_path = os.path.join(tmp_dir, "entrypoint.sh")
                with open(entrypoint_path, "w") as f:
                    f.write(entrypoint_script)

                # Create a file with environment variable names (no values)
                env_names_path = os.path.join(tmp_dir, "mcp-envs.txt")
                with open(env_names_path, "w") as f:
                    # Write one env var name per line
                    for env_name in mcp_config.get("env", {}).keys():
                        f.write(f"{env_name}\n")

                # Create a Dockerfile for the proxy
                dockerfile_content = f"""
FROM {mcp_config["proxy_image"]}

# Install Docker CLI (trying multiple package managers to handle different base images)
USER root
RUN (apt-get update && apt-get install -y docker.io) || \\
    (apt-get update && apt-get install -y docker-ce-cli) || \\
    (apk add --no-cache docker-cli) || \\
    (yum install -y docker) || \\
    echo "WARNING: Could not install Docker CLI - will fall back to minimal MCP server"

# Set environment variables for the proxy
ENV MCP_BASE_IMAGE={mcp_config["base_image"]}
ENV MCP_COMMAND="{mcp_config.get("command", "")}"
ENV SSE_PORT={mcp_config["proxy_options"].get("sse_port", 8080)}
ENV SSE_HOST={mcp_config["proxy_options"].get("sse_host", "0.0.0.0")}
ENV ALLOW_ORIGIN={mcp_config["proxy_options"].get("allow_origin", "*")}
ENV DEBUG=1

# Add environment variables from the configuration
{chr(10).join([f'ENV {k}="{v}"' for k, v in mcp_config.get("env", {}).items()])}

# Add env names file and entrypoint script
COPY mcp-envs.txt /mcp-envs.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
"""

                # Write the Dockerfile
                dockerfile_path = os.path.join(tmp_dir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)

                # Build the image
                custom_image_name = f"cubbi_mcp_proxy_{name}"
                logger.info(f"Building custom proxy image: {custom_image_name}")
                self.client.images.build(
                    path=tmp_dir,
                    tag=custom_image_name,
                    rm=True,
                )

                # Format command for the Docker entrypoint arguments
                # The MCP proxy container will handle this internally based on
                # the MCP_BASE_IMAGE and MCP_COMMAND env vars we set
                logger.info(
                    f"Starting MCP proxy with base_image={mcp_config['base_image']}, command={mcp_config.get('command', '')}"
                )

                # Get the SSE port from the proxy options
                sse_port = mcp_config["proxy_options"].get("sse_port", 8080)

                # Check if we need to bind to a host port
                port_bindings = {}
                if mcp_config.get("host_port"):
                    host_port = mcp_config.get("host_port")
                    port_bindings = {f"{sse_port}/tcp": host_port}

                # Create and start the container
                container = self.client.containers.run(
                    image=custom_image_name,
                    name=container_name,
                    detach=True,
                    network=None,  # Start without network, we'll add it with aliases
                    volumes={
                        "/var/run/docker.sock": {
                            "bind": "/var/run/docker.sock",
                            "mode": "rw",
                        }
                    },
                    labels={
                        "cubbi.mcp": "true",
                        "cubbi.mcp.name": name,
                        "cubbi.mcp.type": "proxy",
                    },
                    ports=port_bindings,  # Bind the SSE port to the host if configured
                )

                # Connect to the inspector network
                network = self.client.networks.get(network_name)
                network.connect(container, aliases=[name])
                logger.info(
                    f"Connected MCP server '{name}' to inspector network {network_name} with alias '{name}'"
                )

                # Create and connect to a dedicated network for session connections
                dedicated_network_name = self._get_mcp_dedicated_network(name)
                try:
                    dedicated_network = self.client.networks.get(dedicated_network_name)
                except DockerException:
                    dedicated_network = self.client.networks.create(
                        dedicated_network_name, driver="bridge"
                    )

                dedicated_network.connect(container, aliases=[name])
                logger.info(
                    f"Connected MCP server '{name}' to dedicated network {dedicated_network_name} with alias '{name}'"
                )

                return {
                    "container_id": container.id,
                    "status": "running",
                    "name": name,
                }

        else:
            raise ValueError(f"Unsupported MCP type: {mcp_type}")

    def stop_mcp(self, name: str) -> bool:
        """Stop an MCP server container.

        Args:
            name: The name of the MCP server to stop

        Returns:
            True if the operation was successful (including cases where the container doesn't exist)
        """
        if not self.client:
            logger.warning("Docker client is not available")
            return False

        # Get the MCP configuration - don't raise an exception if not found
        mcp_config = self.get_mcp(name)
        if not mcp_config:
            logger.warning(
                f"MCP server '{name}' not found, but continuing with removal"
            )
            return True

        # Remote MCPs don't have containers to stop
        if mcp_config.get("type") == "remote":
            return True

        # Get the container name
        container_name = self.get_mcp_container_name(name)

        # Try to get, stop, and remove the container
        try:
            container = self.client.containers.get(container_name)

            # Stop the container if it's running
            if container.status == "running":
                logger.info(f"Stopping MCP container '{name}'...")
                container.stop(timeout=10)

            # Remove the container regardless of its status
            logger.info(f"Removing MCP container '{name}'...")
            container.remove(force=True)
            return True

        except NotFound:
            # Container doesn't exist - this is fine when removing
            logger.info(f"MCP container '{name}' not found, nothing to stop or remove")
            return True
        except Exception as e:
            # Log the error but don't fail the removal operation
            logger.error(f"Error stopping/removing MCP container: {e}")
            return True  # Return true anyway to continue with removal

    def restart_mcp(self, name: str) -> Dict[str, Any]:
        """Restart an MCP server container."""
        if not self.client:
            raise Exception("Docker client is not available")

        # Get the MCP configuration
        mcp_config = self.get_mcp(name)
        if not mcp_config:
            raise ValueError(f"MCP server '{name}' not found")

        # Remote MCPs don't have containers to restart
        if mcp_config.get("type") == "remote":
            return {
                "status": "not_applicable",
                "name": name,
                "type": "remote",
            }

        # Get the container name
        container_name = self.get_mcp_container_name(name)

        # Try to get and restart the container
        try:
            container = self.client.containers.get(container_name)
            container.restart(timeout=10)
            return {
                "container_id": container.id,
                "status": "running",
                "name": name,
            }
        except NotFound:
            # Container doesn't exist, start it
            return self.start_mcp(name)
        except Exception as e:
            logger.error(f"Error restarting MCP container: {e}")
            raise

    def get_mcp_status(self, name: str) -> Dict[str, Any]:
        """Get the status of an MCP server."""
        if not self.client:
            raise Exception("Docker client is not available")

        # Get the MCP configuration
        mcp_config = self.get_mcp(name)
        if not mcp_config:
            raise ValueError(f"MCP server '{name}' not found")

        # Remote MCPs don't have containers
        if mcp_config.get("type") == "remote":
            return {
                "status": "not_applicable",
                "name": name,
                "type": "remote",
                "url": mcp_config.get("url"),
            }

        # Get the container name
        container_name = self.get_mcp_container_name(name)

        # Try to get the container status
        try:
            container = self.client.containers.get(container_name)
            status = (
                MCPStatus.RUNNING
                if container.status == "running"
                else MCPStatus.STOPPED
            )

            # Get container details
            container_info = container.attrs

            # Extract exposed ports from config
            ports = {}
            if (
                "Config" in container_info
                and "ExposedPorts" in container_info["Config"]
            ):
                # Add all exposed ports
                for port in container_info["Config"]["ExposedPorts"].keys():
                    ports[port] = None

            # Add any ports that might be published
            if (
                "NetworkSettings" in container_info
                and "Ports" in container_info["NetworkSettings"]
            ):
                for port, mappings in container_info["NetworkSettings"][
                    "Ports"
                ].items():
                    if mappings:
                        # Port is bound to host
                        ports[port] = int(mappings[0]["HostPort"])

            return {
                "status": status.value,
                "container_id": container.id,
                "name": name,
                "type": mcp_config.get("type"),
                "image": container_info["Config"]["Image"],
                "ports": ports,
                "created": container_info["Created"],
            }
        except NotFound:
            # Container doesn't exist
            return {
                "status": MCPStatus.NOT_FOUND.value,
                "name": name,
                "type": mcp_config.get("type"),
            }
        except Exception as e:
            logger.error(f"Error getting MCP container status: {e}")
            return {
                "status": MCPStatus.FAILED.value,
                "name": name,
                "error": str(e),
            }

    def get_mcp_logs(self, name: str, tail: int = 100) -> str:
        """Get logs from an MCP server container."""
        if not self.client:
            raise Exception("Docker client is not available")

        # Get the MCP configuration
        mcp_config = self.get_mcp(name)
        if not mcp_config:
            raise ValueError(f"MCP server '{name}' not found")

        # Remote MCPs don't have logs
        if mcp_config.get("type") == "remote":
            return "Remote MCPs don't have local logs"

        # Get the container name
        container_name = self.get_mcp_container_name(name)

        # Try to get the container logs
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
            return logs
        except NotFound:
            # Container doesn't exist
            return f"MCP container '{name}' not found"
        except Exception as e:
            logger.error(f"Error getting MCP container logs: {e}")
            return f"Error getting logs: {str(e)}"

    def list_mcp_containers(self) -> List[MCPContainer]:
        """List all MCP containers."""
        if not self.client:
            raise Exception("Docker client is not available")

        # Get all containers with the cubbi.mcp label
        containers = self.client.containers.list(
            all=True, filters={"label": "cubbi.mcp"}
        )

        result = []
        for container in containers:
            # Get container details
            container_info = container.attrs

            # Extract labels
            labels = container_info["Config"]["Labels"]

            # Extract exposed ports from config
            ports = {}
            if (
                "Config" in container_info
                and "ExposedPorts" in container_info["Config"]
            ):
                # Add all exposed ports
                for port in container_info["Config"]["ExposedPorts"].keys():
                    ports[port] = None

            # Add any ports that might be published
            if (
                "NetworkSettings" in container_info
                and "Ports" in container_info["NetworkSettings"]
            ):
                for port, mappings in container_info["NetworkSettings"][
                    "Ports"
                ].items():
                    if mappings:
                        # Port is bound to host
                        ports[port] = int(mappings[0]["HostPort"])

            # Determine status
            status = (
                MCPStatus.RUNNING
                if container.status == "running"
                else MCPStatus.STOPPED
            )

            # Create MCPContainer object
            mcp_container = MCPContainer(
                name=labels.get("cubbi.mcp.name", "unknown"),
                container_id=container.id,
                status=status,
                image=container_info["Config"]["Image"],
                ports=ports,
                created_at=container_info["Created"],
                type=labels.get("cubbi.mcp.type", "unknown"),
            )

            result.append(mcp_container)

        return result
