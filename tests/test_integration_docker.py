"""
Integration tests for Docker interactions in Cubbi Container.
These tests require Docker to be running.
"""

import subprocess
import time
import uuid

# Import the requires_docker decorator from conftest
from conftest import requires_docker


def execute_command_in_container(container_id, command):
    """Execute a command in a Docker container and return the output."""
    result = subprocess.run(
        ["docker", "exec", container_id, "bash", "-c", command],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@requires_docker
def test_integration_session_create_with_volumes(container_manager, test_file_content):
    """Test creating a session with a volume mount."""
    test_file, test_content = test_file_content
    session = None

    try:
        # Create a session with a volume mount
        session = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-volume-{uuid.uuid4().hex[:8]}",
            mount_local=False,  # Don't mount current directory
            volumes={str(test_file): {"bind": "/test/volume_test.txt", "mode": "ro"}},
        )

        assert session is not None
        assert session.status == "running"

        # Give container time to fully start
        time.sleep(2)

        # Verify the file exists in the container and has correct content
        container_content = execute_command_in_container(
            session.container_id, "cat /test/volume_test.txt"
        )

        assert container_content == test_content

    finally:
        # Clean up the container
        if session and session.container_id:
            container_manager.close_session(session.id)


@requires_docker
def test_integration_session_create_with_networks(
    container_manager, docker_test_network
):
    """Test creating a session connected to a custom network."""
    session = None

    try:
        # Create a session with the test network
        session = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-network-{uuid.uuid4().hex[:8]}",
            mount_local=False,  # Don't mount current directory
            networks=[docker_test_network],
        )

        assert session is not None
        assert session.status == "running"

        # Give container time to fully start
        time.sleep(2)

        # Verify the container is connected to the test network
        # Use inspect to check network connections
        import docker

        client = docker.from_env()
        container = client.containers.get(session.container_id)
        container_networks = container.attrs["NetworkSettings"]["Networks"]

        # Container should be connected to both the default cubbi-network and our test network
        assert docker_test_network in container_networks

        # Verify network interface exists in container
        network_interfaces = execute_command_in_container(
            session.container_id, "ip link show | grep -v 'lo' | wc -l"
        )

        # Should have at least 2 interfaces (eth0 for cubbi-network, eth1 for test network)
        assert int(network_interfaces) >= 2

    finally:
        # Clean up the container
        if session and session.container_id:
            container_manager.close_session(session.id)
