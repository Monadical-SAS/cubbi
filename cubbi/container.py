import concurrent.futures
import hashlib
import logging
import os
import pathlib
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import docker
import yaml
from docker.errors import DockerException, ImageNotFound

from .config import ConfigManager
from .mcp import MCPManager
from .models import Image, Session, SessionStatus
from .session import SessionManager
from .user_config import UserConfigManager

# Configure logging
logger = logging.getLogger(__name__)


class ContainerManager:
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        session_manager: Optional[SessionManager] = None,
        user_config_manager: Optional[UserConfigManager] = None,
    ):
        self.config_manager = config_manager or ConfigManager()
        self.session_manager = session_manager or SessionManager()
        self.user_config_manager = user_config_manager or UserConfigManager()
        self.mcp_manager = MCPManager(config_manager=self.user_config_manager)

        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
        except DockerException as e:
            logger.error(f"Error connecting to Docker: {e}")
            print(f"Error connecting to Docker: {e}")
            sys.exit(1)

    def _ensure_network(self) -> None:
        """Ensure the Cubbi network exists"""
        network_name = self.config_manager.config.docker.get("network", "cubbi-network")
        networks = self.client.networks.list(names=[network_name])
        if not networks:
            self.client.networks.create(network_name, driver="bridge")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return str(uuid.uuid4())[:8]

    def _get_project_config_path(
        self, project: Optional[str] = None, project_name: Optional[str] = None
    ) -> Optional[pathlib.Path]:
        """Get the path to the project configuration directory

        Args:
            project: Optional project repository URL or path (only used for mounting).
            project_name: Optional explicit project name. Only used if specified.

        Returns:
            Path to the project configuration directory, or None if no project_name is provided
        """
        # Get home directory for the Cubbi config
        cubbi_home = pathlib.Path.home() / ".cubbi"

        # Only use project_name if explicitly provided
        if project_name:
            # Create a hash of the project name to use as directory name
            project_hash = hashlib.md5(project_name.encode()).hexdigest()

            # Create the project config directory path
            config_path = cubbi_home / "projects" / project_hash / "config"

            # Create the directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.mkdir(exist_ok=True)

            return config_path
        else:
            # If no project_name is provided, don't create any config directory
            # This ensures we don't mount the /cubbi-config volume for project-less sessions
            return None

    def _generate_container_config(
        self,
        image_name: str,
        project_url: Optional[str] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        model: Optional[str] = None,
        ssh: bool = False,
        run_command: Optional[str] = None,
        no_shell: bool = False,
        mcp_list: Optional[List[str]] = None,
        persistent_links: Optional[List[Dict[str, str]]] = None,
    ) -> Path:
        """Generate container configuration YAML file"""

        providers = {}
        for name, provider in self.user_config_manager.list_providers().items():
            api_key = provider.get("api_key", "")
            if api_key.startswith("${") and api_key.endswith("}"):
                env_var = api_key[2:-1]
                api_key = os.environ.get(env_var, "")

            provider_config = {
                "type": provider.get("type"),
                "api_key": api_key,
            }
            if provider.get("base_url"):
                provider_config["base_url"] = provider.get("base_url")
            if provider.get("models"):
                provider_config["models"] = provider.get("models")

            providers[name] = provider_config

        mcps = []
        if mcp_list:
            for mcp_name in mcp_list:
                mcp_config = self.mcp_manager.get_mcp(mcp_name)
                if mcp_config:
                    mcps.append(mcp_config)

        config = {
            "version": "1.0",
            "user": {"uid": uid or 1000, "gid": gid or 1000},
            "providers": providers,
            "mcps": mcps,
            "project": {
                "config_dir": "/cubbi-config",
                "image_config_dir": f"/cubbi-config/{image_name}",
            },
            "ssh": {"enabled": ssh},
        }

        if project_url:
            config["project"]["url"] = project_url

        if persistent_links:
            config["persistent_links"] = persistent_links

        if model:
            config["defaults"] = {"model": model}

        if run_command:
            config["run_command"] = run_command

        config["no_shell"] = no_shell

        config_file = Path(tempfile.mkdtemp()) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Set restrictive permissions (0o600 = read/write for owner only)
        config_file.chmod(0o600)

        # Set ownership to cubbi user if uid/gid are provided
        if uid is not None and gid is not None:
            try:
                os.chown(config_file, uid, gid)
            except (OSError, PermissionError):
                # If we can't chown (e.g., running as non-root), just log and continue
                logger.warning(f"Could not set ownership of config file to {uid}:{gid}")

        return config_file

    def list_sessions(self) -> List[Session]:
        """List all active Cubbi sessions"""
        sessions = []
        try:
            containers = self.client.containers.list(
                all=True, filters={"label": "cubbi.session"}
            )

            for container in containers:
                container_id = container.id
                labels = container.labels

                session_id = labels.get("cubbi.session.id")
                if not session_id:
                    continue

                status = SessionStatus.RUNNING
                if container.status == "exited":
                    status = SessionStatus.STOPPED
                elif container.status == "created":
                    status = SessionStatus.CREATING

                # Get MCP list from container labels
                mcps_str = labels.get("cubbi.mcps", "")
                mcps = (
                    [mcp.strip() for mcp in mcps_str.split(",") if mcp.strip()]
                    if mcps_str
                    else []
                )

                session = Session(
                    id=session_id,
                    name=labels.get("cubbi.session.name", f"cubbi-{session_id}"),
                    image=labels.get("cubbi.image", "unknown"),
                    status=status,
                    container_id=container_id,
                    mcps=mcps,
                )

                # Get port mappings
                if container.attrs.get("NetworkSettings", {}).get("Ports"):
                    ports = {}
                    for container_port, host_ports in container.attrs[
                        "NetworkSettings"
                    ]["Ports"].items():
                        if host_ports:
                            # Strip /tcp or /udp suffix and convert to int
                            container_port_num = int(container_port.split("/")[0])
                            host_port = int(host_ports[0]["HostPort"])
                            ports[container_port_num] = host_port
                    session.ports = ports

                sessions.append(session)

        except DockerException as e:
            print(f"Error listing sessions: {e}")

        return sessions

    def create_session(
        self,
        image_name: str,
        project: Optional[str] = None,
        project_name: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        session_name: Optional[str] = None,
        mount_local: bool = False,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        networks: Optional[List[str]] = None,
        ports: Optional[List[int]] = None,
        mcp: Optional[List[str]] = None,
        run_command: Optional[str] = None,
        no_shell: bool = False,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        model: Optional[str] = None,
        ssh: bool = False,
        domains: Optional[List[str]] = None,
    ) -> Optional[Session]:
        """Create a new Cubbi session

        Args:
            image_name: The name of the image to use
            project: Optional project repository URL or local directory path
            project_name: Optional explicit project name for configuration persistence
            environment: Optional environment variables
            session_name: Optional session name
            mount_local: Whether to mount the specified local directory to /app (ignored if project is None)
            volumes: Optional additional volumes to mount (dict of {host_path: {"bind": container_path, "mode": mode}})
            run_command: Optional command to execute before starting the shell
            no_shell: Whether to close the container after run_command completes (requires run_command)
            networks: Optional list of additional Docker networks to connect to
            mcp: Optional list of MCP server names to attach to the session
            uid: Optional user ID for the container process
            gid: Optional group ID for the container process
            model: Optional model specification in 'provider/model' format (e.g., 'anthropic/claude-3-5-sonnet')
                   Legacy separate model and provider parameters are also supported for backward compatibility
            ssh: Whether to start the SSH server in the container (default: False)
            domains: Optional list of domains to restrict network access to (uses network-filter)
        """
        try:
            # Try to get image from config first
            image = self.config_manager.get_image(image_name)
            if not image:
                # If not found in config, treat it as a Docker image name
                print(
                    f"Image '{image_name}' not found in Cubbi config, using as Docker image..."
                )
                image = Image(
                    name=image_name,
                    description=f"Docker image: {image_name}",
                    version="latest",
                    maintainer="unknown",
                    image=image_name,
                    ports=[],
                    volumes=[],
                    persistent_configs=[],
                )

            # Generate session ID and name
            session_id = self._generate_session_id()
            if not session_name:
                session_name = f"cubbi-{session_id}"

            # Ensure network exists
            self._ensure_network()

            # Minimal environment variables
            env_vars = environment or {}
            env_vars["CUBBI_CONFIG_FILE"] = "/cubbi/config.yaml"

            # Forward specified environment variables from the host to the container
            if (
                hasattr(image, "environments_to_forward")
                and image.environments_to_forward
            ):
                for env_name in image.environments_to_forward:
                    env_value = os.environ.get(env_name)
                    if env_value is not None:
                        env_vars[env_name] = env_value
                        print(
                            f"Forwarding environment variable {env_name} to container"
                        )

            # Pull image if needed
            try:
                self.client.images.get(image.image)
            except ImageNotFound:
                print(f"Pulling image {image.image}...")
                self.client.images.pull(image.image)

            # Set up volume mounts
            session_volumes = {}

            # Determine if project is a local directory or a Git repository
            is_local_directory = False
            is_git_repo = False

            if project:
                # Check if project is a local directory
                if os.path.isdir(os.path.expanduser(project)):
                    is_local_directory = True
                else:
                    # If not a local directory, assume it's a Git repo URL
                    is_git_repo = True

            # Handle mounting based on project type
            if is_local_directory and mount_local:
                # Mount the specified local directory to /app in the container
                local_dir = os.path.abspath(os.path.expanduser(project))
                session_volumes[local_dir] = {"bind": "/app", "mode": "rw"}
                print(f"Mounting local directory {local_dir} to /app")
                # Clear project for container environment since we're mounting
                project = None
            elif is_git_repo:
                env_vars["CUBBI_PROJECT_URL"] = project
                print(
                    f"Git repository URL provided - container will clone {project} into /app during initialization"
                )

            # Add user-specified volumes
            if volumes:
                for host_path, mount_spec in volumes.items():
                    container_path = mount_spec["bind"]
                    # Check for conflicts with /app mount
                    if container_path == "/app" and is_local_directory and mount_local:
                        print(
                            "[yellow]Warning: Volume mount to /app conflicts with local directory mount. User-specified mount takes precedence.[/yellow]"
                        )
                        # Remove the local directory mount if there's a conflict
                        if local_dir in session_volumes:
                            del session_volumes[local_dir]

                    # Add the volume
                    session_volumes[host_path] = mount_spec
                    print(f"Mounting volume: {host_path} -> {container_path}")

            # Set up persistent project configuration if project_name is provided
            persistent_links = []
            project_config_path = self._get_project_config_path(project, project_name)
            if project_config_path:
                print(f"Using project configuration directory: {project_config_path}")

                # Mount the project configuration directory
                session_volumes[str(project_config_path)] = {
                    "bind": "/cubbi-config",
                    "mode": "rw",
                }

                # Create image-specific config directories and collect persistent links
                if image.persistent_configs:
                    print("Setting up persistent configuration directories:")
                    for config in image.persistent_configs:
                        # Get target directory path on host
                        target_dir = project_config_path / config.target.removeprefix(
                            "/cubbi-config/"
                        )

                        # Create directory if it's a directory type config
                        if config.type == "directory":
                            dir_existed = target_dir.exists()
                            target_dir.mkdir(parents=True, exist_ok=True)
                            if not dir_existed:
                                print(f"  - Created directory: {target_dir}")
                        # For files, make sure parent directory exists
                        elif config.type == "file":
                            target_dir.parent.mkdir(parents=True, exist_ok=True)

                        # Store persistent link data for config file
                        persistent_links.append(
                            {
                                "source": config.source,
                                "target": config.target,
                                "type": config.type,
                            }
                        )

                        print(
                            f"  - Prepared host path {target_dir} for symlink target {config.target}"
                        )
            else:
                print(
                    "No project_name provided - skipping configuration directory setup."
                )

            # Default Cubbi network
            default_network = self.config_manager.config.docker.get(
                "network", "cubbi-network"
            )

            # Get network list
            network_list = [default_network]

            # Process MCPs if provided
            mcp_configs = []
            mcp_names = []
            mcp_container_names = []

            # Ensure MCP is a list
            mcps_to_process = mcp if isinstance(mcp, list) else []

            # Process each MCP
            for mcp_name in mcps_to_process:
                # Get the MCP configuration
                mcp_config = self.mcp_manager.get_mcp(mcp_name)
                if not mcp_config:
                    print(f"Warning: MCP server '{mcp_name}' not found, skipping")
                    continue

                # Add to the list of processed MCPs
                mcp_configs.append(mcp_config)
                mcp_names.append(mcp_name)

                # Check if the MCP server is running (for Docker-based MCPs)
                if mcp_config.get("type") in ["docker", "proxy"]:
                    # Ensure the MCP is running
                    try:
                        print(f"Ensuring MCP server '{mcp_name}' is running...")
                        self.mcp_manager.start_mcp(mcp_name)

                        # Store container name for later network connection
                        container_name = self.mcp_manager.get_mcp_container_name(
                            mcp_name
                        )
                        mcp_container_names.append(container_name)

                        # Get MCP status to extract endpoint information
                        mcp_status = self.mcp_manager.get_mcp_status(mcp_name)

                    except Exception as e:
                        print(f"Warning: Failed to start MCP server '{mcp_name}': {e}")
                        # Get the container name before trying to remove it from the list
                        try:
                            container_name = self.mcp_manager.get_mcp_container_name(
                                mcp_name
                            )
                            if container_name in mcp_container_names:
                                mcp_container_names.remove(container_name)
                        except Exception:
                            # If we can't get the container name, just continue
                            pass

                elif mcp_config.get("type") == "remote":
                    # Remote MCP - nothing to do here, config will handle it
                    pass

            # Add user-specified networks
            # Default Cubbi network
            default_network = self.config_manager.config.docker.get(
                "network", "cubbi-network"
            )

            # Get network list, ensuring default is first and no duplicates
            network_list_set = {default_network}
            if networks:
                network_list_set.update(networks)
            network_list = (
                [default_network] + [n for n in networks if n != default_network]
                if networks
                else [default_network]
            )

            if networks:
                for network in networks:
                    if network not in network_list:
                        # This check is slightly redundant now but harmless
                        network_list.append(network)
                        print(f"Adding network {network} to session")

            # Determine container command and entrypoint
            container_command = None
            entrypoint = None
            target_shell = "/bin/bash"

            if run_command:
                # Set the container's command to be the final shell (or exit if no_shell is true)
                container_command = [target_shell]
                logger.info(f"Using run command with shell {target_shell}")
                if no_shell:
                    logger.info("Container will exit after run command")
            else:
                # Use default behavior (often defined by image's ENTRYPOINT/CMD)
                container_command = [target_shell]
                logger.info(
                    "Using default container entrypoint/command for interactive shell."
                )

            # Handle network-filter if domains are specified
            network_filter_container = None
            network_mode = None

            if domains:
                # Check for conflicts
                if networks:
                    print(
                        "[yellow]Warning: Cannot use --domains with --network. Using domain restrictions only.[/yellow]"
                    )
                    networks = []
                    network_list = [default_network]

                # Create network-filter container
                network_filter_name = f"cubbi-network-filter-{session_id}"

                # Pull network-filter image if needed
                network_filter_image = "monadicalsas/network-filter:latest"
                try:
                    self.client.images.get(network_filter_image)
                except ImageNotFound:
                    print(f"Pulling network-filter image {network_filter_image}...")
                    self.client.images.pull(network_filter_image)

                # Create and start network-filter container
                print("Creating network-filter container for domain restrictions...")
                try:
                    # First check if a network-filter container already exists with this name
                    try:
                        existing = self.client.containers.get(network_filter_name)
                        print(
                            f"Removing existing network-filter container {network_filter_name}"
                        )
                        existing.stop()
                        existing.remove()
                    except DockerException:
                        pass  # Container doesn't exist, which is fine

                    network_filter_container = self.client.containers.run(
                        image=network_filter_image,
                        name=network_filter_name,
                        hostname=network_filter_name,
                        detach=True,
                        environment={"ALLOWED_DOMAINS": ",".join(domains)},
                        labels={
                            "cubbi.network-filter": "true",
                            "cubbi.session.id": session_id,
                            "cubbi.session.name": session_name,
                        },
                        cap_add=["NET_ADMIN"],  # Required for iptables
                        remove=False,  # Don't auto-remove on stop
                    )

                    # Wait for container to be running
                    import time

                    for i in range(10):  # Wait up to 10 seconds
                        network_filter_container.reload()
                        if network_filter_container.status == "running":
                            break
                        time.sleep(1)
                    else:
                        raise Exception(
                            f"Network-filter container failed to start. Status: {network_filter_container.status}"
                        )

                    # Use container ID instead of name for network_mode
                    network_mode = f"container:{network_filter_container.id}"
                    print(
                        f"Network restrictions enabled for domains: {', '.join(domains)}"
                    )
                    print(f"Using network mode: {network_mode}")

                except Exception as e:
                    print(f"[red]Error creating network-filter container: {e}[/red]")
                    raise

                # Warn about MCP limitations when using network-filter
                if mcp_names:
                    print(
                        "[yellow]Warning: MCP servers may not be accessible when using domain restrictions.[/yellow]"
                    )

            # Generate configuration file
            project_url = project if is_git_repo else None
            config_file_path = self._generate_container_config(
                image_name=image_name,
                project_url=project_url,
                uid=uid,
                gid=gid,
                model=model,
                ssh=ssh,
                run_command=run_command,
                no_shell=no_shell,
                mcp_list=mcp_names,
                persistent_links=persistent_links
                if "persistent_links" in locals()
                else None,
            )

            # Mount config file
            session_volumes[str(config_file_path)] = {
                "bind": "/cubbi/config.yaml",
                "mode": "ro",
            }

            # Create container
            container_params = {
                "image": image.image,
                "name": session_name,
                "detach": True,
                "tty": True,
                "stdin_open": True,
                "environment": env_vars,
                "volumes": session_volumes,
                "labels": {
                    "cubbi.session": "true",
                    "cubbi.session.id": session_id,
                    "cubbi.session.name": session_name,
                    "cubbi.image": image_name,
                    "cubbi.project": project or "",
                    "cubbi.project_name": project_name or "",
                    "cubbi.mcps": ",".join(mcp_names) if mcp_names else "",
                },
                "command": container_command,  # Set the command
                "entrypoint": entrypoint,  # Set the entrypoint (might be None)
            }

            # Add port forwarding if ports are specified
            if ports:
                container_params["ports"] = {f"{port}/tcp": None for port in ports}

            # Use network_mode if domains are specified, otherwise use regular network
            if network_mode:
                container_params["network_mode"] = network_mode
                # Cannot set hostname when using network_mode
            else:
                container_params["hostname"] = session_name
                container_params["network"] = network_list[
                    0
                ]  # Connect to the first network initially

            container = self.client.containers.create(**container_params)

            # Start container
            container.start()

            # Connect to additional networks (after the first one in network_list)
            # Note: Cannot connect to networks when using network_mode
            if len(network_list) > 1 and not network_mode:
                for network_name in network_list[1:]:
                    try:
                        # Get or create the network
                        try:
                            network = self.client.networks.get(network_name)
                        except DockerException:
                            print(f"Network '{network_name}' not found, creating it...")
                            network = self.client.networks.create(
                                network_name, driver="bridge"
                            )

                        # Connect the container to the network with session name as an alias
                        network.connect(container, aliases=[session_name])
                    except DockerException as e:
                        print(f"Error connecting to network {network_name}: {e}")

            # Reload the container to get updated network information
            container.reload()

            # Connect directly to each MCP's dedicated network
            # Note: Cannot connect to networks when using network_mode
            if not network_mode:
                for mcp_name in mcp_names:
                    try:
                        # Get the dedicated network for this MCP
                        dedicated_network_name = f"cubbi-mcp-{mcp_name}-network"

                        try:
                            network = self.client.networks.get(dedicated_network_name)

                            # Connect the session container to the MCP's dedicated network
                            network.connect(container, aliases=[session_name])
                            print(
                                f"Connected session to MCP '{mcp_name}' via dedicated network: {dedicated_network_name}"
                            )
                        except DockerException:
                            # print(
                            #     f"Error connecting to MCP dedicated network '{dedicated_network_name}': {e}"
                            # )
                            # commented out, may be accessible through another attached network, it's
                            # not mandatory here.
                            pass

                    except Exception as e:
                        print(f"Error connecting session to MCP '{mcp_name}': {e}")

            # Connect to additional user-specified networks
            # Note: Cannot connect to networks when using network_mode
            if networks and not network_mode:
                for network_name in networks:
                    # Check if already connected to this network
                    # NetworkSettings.Networks contains a dict where keys are network names
                    existing_networks = (
                        container.attrs.get("NetworkSettings", {})
                        .get("Networks", {})
                        .keys()
                    )
                    if network_name not in existing_networks:
                        try:
                            # Get or create the network
                            try:
                                network = self.client.networks.get(network_name)
                            except DockerException:
                                print(
                                    f"Network '{network_name}' not found, creating it..."
                                )
                                network = self.client.networks.create(
                                    network_name, driver="bridge"
                                )

                            # Connect the container to the network with session name as an alias
                            network.connect(container, aliases=[session_name])
                        except DockerException as e:
                            print(f"Error connecting to network {network_name}: {e}")

            # Get updated port information
            container.reload()
            ports = {}
            if container.attrs.get("NetworkSettings", {}).get("Ports"):
                for container_port, host_ports in container.attrs["NetworkSettings"][
                    "Ports"
                ].items():
                    if host_ports:
                        container_port_num = int(container_port.split("/")[0])
                        host_port = int(host_ports[0]["HostPort"])
                        ports[container_port_num] = host_port

            # Create session object
            session = Session(
                id=session_id,
                name=session_name,
                image=image_name,
                status=SessionStatus.RUNNING,
                container_id=container.id,
                ports=ports,
            )

            # Save session to the session manager
            # Assuming Session model has uid and gid fields added to its definition
            session_data_to_save = session.model_dump(mode="json")
            # uid and gid are already part of the model dump now
            self.session_manager.add_session(session_id, session_data_to_save)

            return session

        except DockerException as e:
            print(f"Error creating session: {e}")

            # Clean up network-filter container if it was created
            if network_filter_container:
                try:
                    network_filter_container.stop()
                    network_filter_container.remove()
                except Exception:
                    pass

            return None

    def close_session(self, session_id: str, kill: bool = False) -> bool:
        """Close a Cubbi session

        Args:
            session_id: The ID of the session to close
            kill: If True, forcefully kill the container instead of graceful stop
        """
        try:
            sessions = self.list_sessions()
            for session in sessions:
                if session.id == session_id:
                    return self._close_single_session(session, kill=kill)

            print(f"Session '{session_id}' not found")
            return False

        except DockerException as e:
            print(f"Error closing session: {e}")
            return False

    def connect_session(self, session_id: str) -> bool:
        """Connect to a running Cubbi session"""
        # Retrieve full session data which should include uid/gid
        session_data = self.session_manager.get_session(session_id)

        if not session_data:
            print(f"Session '{session_id}' not found in session manager.")
            # Fallback: try listing via Docker labels if session data is missing
            sessions = self.list_sessions()
            session_obj = next((s for s in sessions if s.id == session_id), None)
            if not session_obj or not session_obj.container_id:
                print(f"Session '{session_id}' not found via Docker either.")
                return False
            container_id = session_obj.container_id
            print(
                f"[yellow]Warning: Session data missing for {session_id}. Connecting as default container user.[/yellow]"
            )
        else:
            container_id = session_data.get("container_id")
            if not container_id:
                print(f"Container ID not found for session {session_id}.")
                return False

            # Check status from Docker directly
            try:
                container = self.client.containers.get(container_id)
                if container.status != "running":
                    print(
                        f"Session '{session_id}' container is not running (status: {container.status})."
                    )
                    return False
            except docker.errors.NotFound:
                print(f"Container {container_id} for session {session_id} not found.")
                # Clean up potentially stale session data
                self.session_manager.remove_session(session_id)
                return False
            except DockerException as e:
                print(f"Error checking container status for session {session_id}: {e}")
                return False

        try:
            # Use exec instead of attach to avoid container exit on Ctrl+C
            print(
                f"Connecting to session {session_id} (container: {container_id[:12]})..."
            )
            print("Type 'exit' to detach from the session.")

            # Use docker exec to start a new bash process in the container
            # This leverages the init-status.sh script in bash.bashrc
            # which will check initialization status
            cmd = ["docker", "exec", "-it", container_id, "bash", "-l"]

            # Use execvp to replace the current process with docker exec
            # This provides a seamless shell experience
            os.execvp("docker", cmd)
            # execvp does not return if successful
            return True  # Should not be reached if execvp succeeds

        except FileNotFoundError:
            print(
                "[red]Error: 'docker' command not found. Is Docker installed and in your PATH?[/red]"
            )
            return False

        except DockerException as e:
            print(f"Error connecting to session: {e}")
            return False

    def _close_single_session(self, session: Session, kill: bool = False) -> bool:
        """Close a single session (helper for parallel processing)

        Args:
            session: The session to close
            kill: If True, forcefully kill the container instead of graceful stop

        Returns:
            bool: Whether the session was successfully closed
        """
        if not session.container_id:
            return False

        try:
            container = self.client.containers.get(session.container_id)

            try:
                if kill:
                    container.kill()
                else:
                    container.stop()
            except DockerException:
                pass

            container.remove()

            network_filter_name = f"cubbi-network-filter-{session.id}"
            try:
                network_filter_container = self.client.containers.get(
                    network_filter_name
                )
                logger.info(f"Stopping network-filter container {network_filter_name}")
                try:
                    if kill:
                        network_filter_container.kill()
                    else:
                        network_filter_container.stop()
                except DockerException:
                    pass
                network_filter_container.remove()
            except DockerException:
                pass

            self.session_manager.remove_session(session.id)
            return True
        except DockerException as e:
            error_message = str(e).lower()
            if (
                "is not running" in error_message
                or "no such container" in error_message
                or "not found" in error_message
            ):
                print(
                    f"Container already stopped/removed, removing session {session.id} from list"
                )
                self.session_manager.remove_session(session.id)
                return True
            else:
                print(f"Error closing session {session.id}: {e}")
                return False

    def close_all_sessions(
        self, progress_callback=None, kill: bool = False
    ) -> Tuple[int, bool]:
        """Close all Cubbi sessions with parallel processing and progress reporting

        Args:
            progress_callback: Optional callback function to report progress
                The callback should accept (session_id, status, message)
            kill: If True, forcefully kill containers instead of graceful stop

        Returns:
            tuple: (number of sessions closed, success)
        """
        try:
            sessions = self.list_sessions()
            if not sessions:
                return 0, True

            # No need for session status as we receive it via callback

            def close_with_progress(session):
                if not session.container_id:
                    return False

                try:
                    container = self.client.containers.get(session.container_id)

                    try:
                        if kill:
                            container.kill()
                        else:
                            container.stop()
                    except DockerException:
                        pass

                    container.remove()

                    network_filter_name = f"cubbi-network-filter-{session.id}"
                    try:
                        network_filter_container = self.client.containers.get(
                            network_filter_name
                        )
                        try:
                            if kill:
                                network_filter_container.kill()
                            else:
                                network_filter_container.stop()
                        except DockerException:
                            pass
                        network_filter_container.remove()
                    except DockerException:
                        pass

                    self.session_manager.remove_session(session.id)

                    if progress_callback:
                        progress_callback(
                            session.id,
                            "completed",
                            f"{session.name} closed successfully",
                        )

                    return True
                except DockerException as e:
                    error_message = str(e).lower()
                    if (
                        "is not running" in error_message
                        or "no such container" in error_message
                        or "not found" in error_message
                    ):
                        print(
                            f"Container already stopped/removed, removing session {session.id} from list"
                        )
                        self.session_manager.remove_session(session.id)
                        if progress_callback:
                            progress_callback(
                                session.id,
                                "completed",
                                f"{session.name} removed from list (container already stopped)",
                            )
                        return True
                    else:
                        error_msg = f"Error: {str(e)}"
                        if progress_callback:
                            progress_callback(session.id, "failed", error_msg)
                        print(f"Error closing session {session.id}: {e}")
                        return False

            # Use ThreadPoolExecutor to close sessions in parallel
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(10, len(sessions))
            ) as executor:
                # Submit all session closing tasks
                future_to_session = {
                    executor.submit(close_with_progress, session): session
                    for session in sessions
                }

                # Collect results
                closed_count = 0
                for future in concurrent.futures.as_completed(future_to_session):
                    session = future_to_session[future]
                    try:
                        success = future.result()
                        if success:
                            closed_count += 1
                    except Exception as e:
                        print(f"Error closing session {session.id}: {e}")

            return closed_count, closed_count > 0

        except DockerException as e:
            print(f"Error closing all sessions: {e}")
            return 0, False

    def get_session_logs(self, session_id: str, follow: bool = False) -> Optional[str]:
        """Get logs from a Cubbi session"""
        try:
            sessions = self.list_sessions()
            for session in sessions:
                if session.id == session_id and session.container_id:
                    container = self.client.containers.get(session.container_id)
                    if follow:
                        # For streamed logs, we'll buffer by line to avoid character-by-character output
                        import io
                        from typing import Iterator

                        def process_log_stream(
                            stream: Iterator[bytes],
                        ) -> Iterator[str]:
                            buffer = io.StringIO()
                            for chunk in stream:
                                chunk_str = chunk.decode("utf-8", errors="replace")
                                buffer.write(chunk_str)

                                # Process complete lines
                                while True:
                                    line = buffer.getvalue()
                                    newline_pos = line.find("\n")
                                    if newline_pos == -1:
                                        break

                                    # Extract complete line and yield it
                                    complete_line = line[:newline_pos].rstrip()
                                    yield complete_line

                                    # Update buffer to contain only the remaining content
                                    new_buffer = io.StringIO()
                                    new_buffer.write(line[newline_pos + 1 :])
                                    buffer = new_buffer

                            # Don't forget to yield any remaining content at the end
                            final_content = buffer.getvalue().strip()
                            if final_content:
                                yield final_content

                        try:
                            # Process the log stream line by line
                            for line in process_log_stream(
                                container.logs(stream=True, follow=True)
                            ):
                                print(line)
                        except KeyboardInterrupt:
                            # Handle Ctrl+C gracefully
                            print("\nStopped following logs.")

                        return None
                    else:
                        return container.logs().decode()

            print(f"Session '{session_id}' not found")
            return None

        except DockerException as e:
            print(f"Error getting session logs: {e}")
            return None

    def get_init_logs(self, session_id: str, follow: bool = False) -> Optional[str]:
        """Get initialization logs from a Cubbi session

        Args:
            session_id: The session ID
            follow: Whether to follow the logs

        Returns:
            The logs as a string, or None if there was an error
        """
        try:
            sessions = self.list_sessions()
            for session in sessions:
                if session.id == session_id and session.container_id:
                    container = self.client.containers.get(session.container_id)

                    # Check if initialization is complete
                    init_complete = False
                    try:
                        exit_code, output = container.exec_run(
                            "grep -q 'INIT_COMPLETE=true' /init.status"
                        )
                        init_complete = exit_code == 0
                    except DockerException:
                        pass

                    if follow and not init_complete:
                        print(
                            f"Following initialization logs for session {session_id}..."
                        )
                        print("Press Ctrl+C to stop following")

                        import io

                        def process_exec_stream(stream):
                            buffer = io.StringIO()
                            for chunk_type, chunk_bytes in stream:
                                if chunk_type != 1:  # Skip stderr (type 2)
                                    continue

                                chunk_str = chunk_bytes.decode(
                                    "utf-8", errors="replace"
                                )
                                buffer.write(chunk_str)

                                # Process complete lines
                                while True:
                                    line = buffer.getvalue()
                                    newline_pos = line.find("\n")
                                    if newline_pos == -1:
                                        break

                                    # Extract complete line and yield it
                                    complete_line = line[:newline_pos].rstrip()
                                    yield complete_line

                                    # Update buffer to contain only the remaining content
                                    new_buffer = io.StringIO()
                                    new_buffer.write(line[newline_pos + 1 :])
                                    buffer = new_buffer

                            # Don't forget to yield any remaining content at the end
                            final_content = buffer.getvalue().strip()
                            if final_content:
                                yield final_content

                        try:
                            exec_result = container.exec_run(
                                "tail -f /init.log", stream=True, demux=True
                            )

                            # Process the exec stream line by line
                            for line in process_exec_stream(exec_result[1]):
                                print(line)
                        except KeyboardInterrupt:
                            print("\nStopped following logs.")

                        return None
                    else:
                        exit_code, output = container.exec_run("cat /init.log")
                        if exit_code == 0:
                            return output.decode()
                        else:
                            print("No initialization logs found")
                            return None

            print(f"Session '{session_id}' not found")
            return None

        except DockerException as e:
            print(f"Error getting initialization logs: {e}")
            return None
