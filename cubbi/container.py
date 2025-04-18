import concurrent.futures
import hashlib
import logging
import os
import pathlib
import sys
import uuid
from typing import Dict, List, Optional, Tuple

import docker
from docker.errors import DockerException, ImageNotFound

from .config import ConfigManager
from .mcp import MCPManager
from .models import Session, SessionStatus
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

                session = Session(
                    id=session_id,
                    name=labels.get("cubbi.session.name", f"cubbi-{session_id}"),
                    image=labels.get("cubbi.image", "unknown"),
                    status=status,
                    container_id=container_id,
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
        mcp: Optional[List[str]] = None,
        run_command: Optional[str] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        ssh: bool = False,
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
            networks: Optional list of additional Docker networks to connect to
            mcp: Optional list of MCP server names to attach to the session
            uid: Optional user ID for the container process
            gid: Optional group ID for the container process
            ssh: Whether to start the SSH server in the container (default: False)
        """
        try:
            # Validate image exists
            image = self.config_manager.get_image(image_name)
            if not image:
                print(f"Image '{image_name}' not found")
                return None

            # Generate session ID and name
            session_id = self._generate_session_id()
            if not session_name:
                session_name = f"cubbi-{session_id}"

            # Ensure network exists
            self._ensure_network()

            # Prepare environment variables
            env_vars = environment or {}

            # Add CUBBI_USER_ID and CUBBI_GROUP_ID for entrypoint script
            env_vars["CUBBI_USER_ID"] = str(uid) if uid is not None else "1000"
            env_vars["CUBBI_GROUP_ID"] = str(gid) if gid is not None else "1000"

            # Set SSH environment variable
            env_vars["CUBBI_SSH_ENABLED"] = "true" if ssh else "false"

            # Pass API keys from host environment to container for local development
            api_keys = [
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "OPENROUTER_API_KEY",
                "GOOGLE_API_KEY",
                "LANGFUSE_INIT_PROJECT_PUBLIC_KEY",
                "LANGFUSE_INIT_PROJECT_SECRET_KEY",
                "LANGFUSE_URL",
            ]
            for key in api_keys:
                if key in os.environ and key not in env_vars:
                    env_vars[key] = os.environ[key]

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
            project_config_path = self._get_project_config_path(project, project_name)
            if project_config_path:
                print(f"Using project configuration directory: {project_config_path}")

                # Mount the project configuration directory
                session_volumes[str(project_config_path)] = {
                    "bind": "/cubbi-config",
                    "mode": "rw",
                }

                # Add environment variables for config path
                env_vars["CUBBI_CONFIG_DIR"] = "/cubbi-config"
                env_vars["CUBBI_IMAGE_CONFIG_DIR"] = f"/cubbi-config/{image_name}"

                # Create image-specific config directories and set up direct volume mounts
                if image.persistent_configs:
                    persistent_links_data = []  # To store "source:target" pairs for symlinks
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
                            # File will be created by the container if needed

                        # Store the source and target paths for the init script
                        # Note: config.target is the path *within* /cubbi-config
                        persistent_links_data.append(f"{config.source}:{config.target}")

                        print(
                            f"  - Prepared host path {target_dir} for symlink target {config.target}"
                        )

                    # Set up persistent links
                    if persistent_links_data:
                        env_vars["CUBBI_PERSISTENT_LINKS"] = ";".join(
                            persistent_links_data
                        )
                        print(
                            f"Setting CUBBI_PERSISTENT_LINKS={env_vars['CUBBI_PERSISTENT_LINKS']}"
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

                        # Add MCP environment variables with index
                        idx = len(mcp_names) - 1  # 0-based index for the current MCP

                        if mcp_config.get("type") == "remote":
                            # For remote MCP, set the URL and headers
                            env_vars[f"MCP_{idx}_URL"] = mcp_config.get("url")
                            if mcp_config.get("headers"):
                                # Serialize headers as JSON
                                import json

                                env_vars[f"MCP_{idx}_HEADERS"] = json.dumps(
                                    mcp_config.get("headers")
                                )
                        else:
                            # For Docker/proxy MCP, set the connection details
                            # Use both the container name and the short name for internal Docker DNS resolution
                            container_name = self.mcp_manager.get_mcp_container_name(
                                mcp_name
                            )
                            # Use the short name (mcp_name) as the primary hostname
                            env_vars[f"MCP_{idx}_HOST"] = mcp_name
                            # Default port is 8080 unless specified in status
                            port = next(
                                iter(mcp_status.get("ports", {}).values()), 8080
                            )
                            env_vars[f"MCP_{idx}_PORT"] = str(port)
                            # Use the short name in the URL to take advantage of the network alias
                            env_vars[f"MCP_{idx}_URL"] = f"http://{mcp_name}:{port}/sse"
                            # For backward compatibility, also set the full container name URL
                            env_vars[f"MCP_{idx}_CONTAINER_URL"] = (
                                f"http://{container_name}:{port}/sse"
                            )

                        # Set type-specific information
                        env_vars[f"MCP_{idx}_TYPE"] = mcp_config.get("type")
                        env_vars[f"MCP_{idx}_NAME"] = mcp_name

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
                    # For remote MCP, just set environment variables
                    idx = len(mcp_names) - 1  # 0-based index for the current MCP

                    env_vars[f"MCP_{idx}_URL"] = mcp_config.get("url")
                    if mcp_config.get("headers"):
                        # Serialize headers as JSON
                        import json

                        env_vars[f"MCP_{idx}_HEADERS"] = json.dumps(
                            mcp_config.get("headers")
                        )

                    # Set type-specific information
                    env_vars[f"MCP_{idx}_TYPE"] = "remote"
                    env_vars[f"MCP_{idx}_NAME"] = mcp_name

            # Set environment variables for MCP count if we have any
            if mcp_names:
                env_vars["MCP_COUNT"] = str(len(mcp_names))
                env_vars["MCP_ENABLED"] = "true"
                # Serialize all MCP names as JSON
                import json

                env_vars["MCP_NAMES"] = json.dumps(mcp_names)

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
                # Set environment variable for cubbi-init.sh to pick up
                env_vars["CUBBI_RUN_COMMAND"] = run_command
                # Set the container's command to be the final shell
                container_command = [target_shell]
                logger.info(
                    f"Setting CUBBI_RUN_COMMAND and targeting shell {target_shell}"
                )
            else:
                # Use default behavior (often defined by image's ENTRYPOINT/CMD)
                # Set the container's command to be the final shell if none specified by Dockerfile CMD
                # Note: Dockerfile CMD is ["tail", "-f", "/dev/null"], so this might need adjustment
                # if we want interactive shell by default without --run. Let's default to bash for now.
                container_command = [target_shell]
                logger.info(
                    "Using default container entrypoint/command for interactive shell."
                )

            # Set default model/provider from user config if not explicitly provided
            env_vars["CUBBI_MODEL"] = model or self.user_config_manager.get(
                "defaults.model", ""
            )
            env_vars["CUBBI_PROVIDER"] = provider or self.user_config_manager.get(
                "defaults.provider", ""
            )

            # Create container
            container = self.client.containers.create(
                image=image.image,
                name=session_name,
                hostname=session_name,
                detach=True,
                tty=True,
                stdin_open=True,
                environment=env_vars,
                volumes=session_volumes,
                labels={
                    "cubbi.session": "true",
                    "cubbi.session.id": session_id,
                    "cubbi.session.name": session_name,
                    "cubbi.image": image_name,
                    "cubbi.project": project or "",
                    "cubbi.project_name": project_name or "",
                    "cubbi.mcps": ",".join(mcp_names) if mcp_names else "",
                },
                network=network_list[0],  # Connect to the first network initially
                command=container_command,  # Set the command
                entrypoint=entrypoint,  # Set the entrypoint (might be None)
                ports={f"{port}/tcp": None for port in image.ports},
            )

            # Start container
            container.start()

            # Connect to additional networks (after the first one in network_list)
            if len(network_list) > 1:
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
                        print(
                            f"Connected to network: {network_name} with alias: {session_name}"
                        )
                    except DockerException as e:
                        print(f"Error connecting to network {network_name}: {e}")

            # Reload the container to get updated network information
            container.reload()

            # Connect directly to each MCP's dedicated network
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
                    except DockerException as e:
                        print(
                            f"Error connecting to MCP dedicated network '{dedicated_network_name}': {e}"
                        )

                except Exception as e:
                    print(f"Error connecting session to MCP '{mcp_name}': {e}")

            # Connect to additional user-specified networks
            if networks:
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
                            print(
                                f"Connected to network: {network_name} with alias: {session_name}"
                            )
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
            return None

    def close_session(self, session_id: str) -> bool:
        """Close a Cubbi session"""
        try:
            sessions = self.list_sessions()
            for session in sessions:
                if session.id == session_id:
                    return self._close_single_session(session)

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

    def _close_single_session(self, session: Session) -> bool:
        """Close a single session (helper for parallel processing)

        Args:
            session: The session to close

        Returns:
            bool: Whether the session was successfully closed
        """
        if not session.container_id:
            return False

        try:
            container = self.client.containers.get(session.container_id)
            container.stop()
            container.remove()
            self.session_manager.remove_session(session.id)
            return True
        except DockerException as e:
            print(f"Error closing session {session.id}: {e}")
            return False

    def close_all_sessions(self, progress_callback=None) -> Tuple[int, bool]:
        """Close all Cubbi sessions with parallel processing and progress reporting

        Args:
            progress_callback: Optional callback function to report progress
                The callback should accept (session_id, status, message)

        Returns:
            tuple: (number of sessions closed, success)
        """
        try:
            sessions = self.list_sessions()
            if not sessions:
                return 0, True

            # No need for session status as we receive it via callback

            # Define a wrapper to track progress
            def close_with_progress(session):
                if not session.container_id:
                    return False

                try:
                    container = self.client.containers.get(session.container_id)
                    # Stop and remove container
                    container.stop()
                    container.remove()
                    # Remove from session storage
                    self.session_manager.remove_session(session.id)

                    # Notify about completion
                    if progress_callback:
                        progress_callback(
                            session.id,
                            "completed",
                            f"{session.name} closed successfully",
                        )

                    return True
                except DockerException as e:
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
                        for line in container.logs(stream=True, follow=True):
                            print(line.decode().strip())
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
                        container.exec_run(
                            "tail -f /init.log", stream=True, demux=True, tty=True
                        )
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
