import os
import sys
import uuid
import docker
from typing import Dict, List, Optional
from docker.errors import DockerException, ImageNotFound

from .models import Session, SessionStatus
from .config import ConfigManager


class ContainerManager:
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
        except DockerException as e:
            print(f"Error connecting to Docker: {e}")
            sys.exit(1)

    def _ensure_network(self) -> None:
        """Ensure the MC network exists"""
        network_name = self.config_manager.config.docker.get("network", "mc-network")
        networks = self.client.networks.list(names=[network_name])
        if not networks:
            self.client.networks.create(network_name, driver="bridge")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return str(uuid.uuid4())[:8]

    def list_sessions(self) -> List[Session]:
        """List all active MC sessions"""
        sessions = []
        try:
            containers = self.client.containers.list(
                all=True, filters={"label": "mc.session"}
            )

            for container in containers:
                container_id = container.id
                labels = container.labels

                session_id = labels.get("mc.session.id")
                if not session_id:
                    continue

                status = SessionStatus.RUNNING
                if container.status == "exited":
                    status = SessionStatus.STOPPED
                elif container.status == "created":
                    status = SessionStatus.CREATING

                session = Session(
                    id=session_id,
                    name=labels.get("mc.session.name", f"mc-{session_id}"),
                    driver=labels.get("mc.driver", "unknown"),
                    status=status,
                    container_id=container_id,
                    created_at=container.attrs["Created"],
                    project=labels.get("mc.project"),
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
        driver_name: str,
        project: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        session_name: Optional[str] = None,
        mount_local: bool = True,
    ) -> Optional[Session]:
        """Create a new MC session

        Args:
            driver_name: The name of the driver to use
            project: Optional project repository URL
            environment: Optional environment variables
            session_name: Optional session name
            mount_local: Whether to mount the current directory to /app
        """
        try:
            # Validate driver exists
            driver = self.config_manager.get_driver(driver_name)
            if not driver:
                print(f"Driver '{driver_name}' not found")
                return None

            # Generate session ID and name
            session_id = self._generate_session_id()
            if not session_name:
                session_name = f"mc-{session_id}"

            # Ensure network exists
            self._ensure_network()

            # Prepare environment variables
            env_vars = environment or {}

            # Pull image if needed
            try:
                self.client.images.get(driver.image)
            except ImageNotFound:
                print(f"Pulling image {driver.image}...")
                self.client.images.pull(driver.image)

            # Set up volume mounts
            volumes = {}
            if mount_local:
                # Mount current directory to /app in the container
                import os

                current_dir = os.getcwd()
                volumes[current_dir] = {"bind": "/app", "mode": "rw"}
                print(f"Mounting local directory {current_dir} to /app")

            # Create container
            container = self.client.containers.create(
                image=driver.image,
                name=session_name,
                hostname=session_name,
                detach=True,
                tty=True,
                stdin_open=True,
                environment=env_vars,
                volumes=volumes,
                labels={
                    "mc.session": "true",
                    "mc.session.id": session_id,
                    "mc.session.name": session_name,
                    "mc.driver": driver_name,
                    "mc.project": project or "",
                },
                network=self.config_manager.config.docker.get("network", "mc-network"),
                ports={f"{port}/tcp": None for port in driver.ports},
            )

            # Start container
            container.start()

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
                driver=driver_name,
                status=SessionStatus.RUNNING,
                container_id=container.id,
                environment=env_vars,
                project=project,
                created_at=container.attrs["Created"],
                ports=ports,
            )

            # Save session to config as JSON-compatible dict
            self.config_manager.add_session(session_id, session.model_dump(mode="json"))

            return session

        except DockerException as e:
            print(f"Error creating session: {e}")
            return None

    def close_session(self, session_id: str) -> bool:
        """Close a MC session"""
        try:
            sessions = self.list_sessions()
            for session in sessions:
                if session.id == session_id and session.container_id:
                    container = self.client.containers.get(session.container_id)
                    container.stop()
                    container.remove()
                    self.config_manager.remove_session(session_id)
                    return True

            print(f"Session '{session_id}' not found")
            return False

        except DockerException as e:
            print(f"Error closing session: {e}")
            return False

    def connect_session(self, session_id: str) -> bool:
        """Connect to a running MC session"""
        try:
            sessions = self.list_sessions()
            for session in sessions:
                if session.id == session_id and session.container_id:
                    if session.status != SessionStatus.RUNNING:
                        print(f"Session '{session_id}' is not running")
                        return False

                    # Execute interactive shell in container
                    os.system(f"docker exec -it {session.container_id} /bin/bash")
                    return True

            print(f"Session '{session_id}' not found")
            return False

        except DockerException as e:
            print(f"Error connecting to session: {e}")
            return False

    def close_all_sessions(self) -> tuple[int, bool]:
        """Close all MC sessions

        Returns:
            tuple: (number of sessions closed, success)
        """
        try:
            sessions = self.list_sessions()
            if not sessions:
                return 0, True

            count = 0
            for session in sessions:
                if session.container_id:
                    try:
                        container = self.client.containers.get(session.container_id)
                        container.stop()
                        container.remove()
                        self.config_manager.remove_session(session.id)
                        count += 1
                    except DockerException as e:
                        print(f"Error closing session {session.id}: {e}")

            return count, count > 0

        except DockerException as e:
            print(f"Error closing all sessions: {e}")
            return 0, False

    def get_session_logs(self, session_id: str, follow: bool = False) -> Optional[str]:
        """Get logs from a MC session"""
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
