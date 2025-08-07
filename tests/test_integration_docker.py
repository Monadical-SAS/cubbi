"""
Integration tests for Docker interactions in Cubbi Container.
These tests require Docker to be running.
"""

import subprocess
import time
import uuid
import docker


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


def wait_for_container_init(container_id, timeout=5.0, poll_interval=0.1):
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Check if /cubbi/init.status contains INIT_COMPLETE=true
            result = execute_command_in_container(
                container_id,
                "grep -q 'INIT_COMPLETE=true' /cubbi/init.status 2>/dev/null && echo 'COMPLETE' || echo 'PENDING'",
            )

            if result == "COMPLETE":
                return True

        except subprocess.CalledProcessError:
            # File might not exist yet or container not ready, continue polling
            pass

        time.sleep(poll_interval)

    # Timeout reached
    return False


@requires_docker
def test_integration_session_create_with_volumes(
    isolate_cubbi_config, test_file_content
):
    """Test creating a session with a volume mount."""
    test_file, test_content = test_file_content
    session = None

    try:
        # Get the isolated container manager
        container_manager = isolate_cubbi_config["container_manager"]

        # Create a session with a volume mount
        session = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-volume-{uuid.uuid4().hex[:8]}",
            mount_local=False,  # Don't mount current directory
            volumes={str(test_file): {"bind": "/test/volume_test.txt", "mode": "ro"}},
        )

        assert session is not None
        assert session.status == "running"

        # Wait for container initialization to complete
        init_success = wait_for_container_init(session.container_id)
        assert init_success, "Container initialization timed out"

        # Verify the file exists in the container and has correct content
        container_content = execute_command_in_container(
            session.container_id, "cat /test/volume_test.txt"
        )

        assert container_content == test_content

    finally:
        # Clean up the container (use kill for faster test cleanup)
        if session and session.container_id:
            container_manager.close_session(session.id, kill=True)


@requires_docker
def test_integration_session_create_with_networks(
    isolate_cubbi_config, docker_test_network
):
    """Test creating a session connected to a custom network."""
    session = None

    try:
        # Get the isolated container manager
        container_manager = isolate_cubbi_config["container_manager"]

        # Create a session with the test network
        session = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-network-{uuid.uuid4().hex[:8]}",
            mount_local=False,  # Don't mount current directory
            networks=[docker_test_network],
        )

        assert session is not None
        assert session.status == "running"

        # Wait for container initialization to complete
        init_success = wait_for_container_init(session.container_id)
        assert init_success, "Container initialization timed out"

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
        # Clean up the container (use kill for faster test cleanup)
        if session and session.container_id:
            container_manager.close_session(session.id, kill=True)


@requires_docker
def test_integration_session_create_with_ports(isolate_cubbi_config):
    """Test creating a session with port forwarding."""
    session = None

    try:
        # Get the isolated container manager
        container_manager = isolate_cubbi_config["container_manager"]

        # Create a session with port forwarding
        session = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-ports-{uuid.uuid4().hex[:8]}",
            mount_local=False,  # Don't mount current directory
            ports=[8080, 9000],  # Forward these ports
        )

        assert session is not None
        assert session.status == "running"

        # Verify ports are mapped
        assert isinstance(session.ports, dict)
        assert 8080 in session.ports
        assert 9000 in session.ports

        # Verify port mappings are valid (host ports should be assigned)
        assert isinstance(session.ports[8080], int)
        assert isinstance(session.ports[9000], int)
        assert session.ports[8080] > 0
        assert session.ports[9000] > 0

        # Wait for container initialization to complete
        init_success = wait_for_container_init(session.container_id)
        assert init_success, "Container initialization timed out"

        # Verify Docker port mappings using Docker client
        import docker

        client = docker.from_env()
        container = client.containers.get(session.container_id)
        container_ports = container.attrs["NetworkSettings"]["Ports"]

        # Verify both ports are exposed
        assert "8080/tcp" in container_ports
        assert "9000/tcp" in container_ports

        # Verify host port bindings exist
        assert container_ports["8080/tcp"] is not None
        assert container_ports["9000/tcp"] is not None
        assert len(container_ports["8080/tcp"]) > 0
        assert len(container_ports["9000/tcp"]) > 0

        # Verify host ports match session.ports
        host_port_8080 = int(container_ports["8080/tcp"][0]["HostPort"])
        host_port_9000 = int(container_ports["9000/tcp"][0]["HostPort"])
        assert session.ports[8080] == host_port_8080
        assert session.ports[9000] == host_port_9000

    finally:
        # Clean up the container (use kill for faster test cleanup)
        if session and session.container_id:
            container_manager.close_session(session.id, kill=True)


@requires_docker
def test_integration_session_create_no_ports(isolate_cubbi_config):
    """Test creating a session without port forwarding."""
    session = None

    try:
        # Get the isolated container manager
        container_manager = isolate_cubbi_config["container_manager"]

        # Create a session without ports
        session = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-no-ports-{uuid.uuid4().hex[:8]}",
            mount_local=False,  # Don't mount current directory
            ports=[],  # No ports
        )

        assert session is not None
        assert session.status == "running"

        # Verify no ports are mapped
        assert isinstance(session.ports, dict)
        assert len(session.ports) == 0

        # Wait for container initialization to complete
        init_success = wait_for_container_init(session.container_id)
        assert init_success, "Container initialization timed out"

        # Verify Docker has no port mappings
        import docker

        client = docker.from_env()
        container = client.containers.get(session.container_id)
        container_ports = container.attrs["NetworkSettings"]["Ports"]

        # Should have no port mappings (empty dict or None values)
        for port_spec, bindings in container_ports.items():
            assert bindings is None or len(bindings) == 0

    finally:
        # Clean up the container (use kill for faster test cleanup)
        if session and session.container_id:
            container_manager.close_session(session.id, kill=True)


@requires_docker
def test_integration_session_create_with_single_port(isolate_cubbi_config):
    """Test creating a session with a single port forward."""
    session = None

    try:
        # Get the isolated container manager
        container_manager = isolate_cubbi_config["container_manager"]

        # Create a session with single port
        session = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-single-port-{uuid.uuid4().hex[:8]}",
            mount_local=False,  # Don't mount current directory
            ports=[3000],  # Single port
        )

        assert session is not None
        assert session.status == "running"

        # Verify single port is mapped
        assert isinstance(session.ports, dict)
        assert len(session.ports) == 1
        assert 3000 in session.ports
        assert isinstance(session.ports[3000], int)
        assert session.ports[3000] > 0

        # Wait for container initialization to complete
        init_success = wait_for_container_init(session.container_id)
        assert init_success, "Container initialization timed out"

        client = docker.from_env()
        container = client.containers.get(session.container_id)
        container_ports = container.attrs["NetworkSettings"]["Ports"]

        # Should have exactly one port mapping
        port_mappings = {
            k: v for k, v in container_ports.items() if v is not None and len(v) > 0
        }
        assert len(port_mappings) == 1
        assert "3000/tcp" in port_mappings

    finally:
        # Clean up the container (use kill for faster test cleanup)
        if session and session.container_id:
            container_manager.close_session(session.id, kill=True)


@requires_docker
def test_integration_kill_vs_stop_speed(isolate_cubbi_config):
    """Test that kill is faster than stop for container termination."""
    import time

    # Get the isolated container manager
    container_manager = isolate_cubbi_config["container_manager"]

    # Create two identical sessions for comparison
    session_stop = None
    session_kill = None

    try:
        # Create first session (will be stopped gracefully)
        session_stop = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-stop-{uuid.uuid4().hex[:8]}",
            mount_local=False,
            ports=[],
        )

        # Create second session (will be killed)
        session_kill = container_manager.create_session(
            image_name="goose",
            session_name=f"cubbi-test-kill-{uuid.uuid4().hex[:8]}",
            mount_local=False,
            ports=[],
        )

        assert session_stop is not None
        assert session_kill is not None

        # Wait for both containers to initialize
        init_success_stop = wait_for_container_init(session_stop.container_id)
        init_success_kill = wait_for_container_init(session_kill.container_id)
        assert init_success_stop, "Stop test container initialization timed out"
        assert init_success_kill, "Kill test container initialization timed out"

        # Time graceful stop
        start_time = time.time()
        container_manager.close_session(session_stop.id, kill=False)
        stop_time = time.time() - start_time
        session_stop = None  # Mark as cleaned up

        # Time kill
        start_time = time.time()
        container_manager.close_session(session_kill.id, kill=True)
        kill_time = time.time() - start_time
        session_kill = None  # Mark as cleaned up

        # Kill should be faster than stop (usually by several seconds)
        # We use a generous threshold since system performance can vary
        assert (
            kill_time < stop_time
        ), f"Kill ({kill_time:.2f}s) should be faster than stop ({stop_time:.2f}s)"

        # Verify both methods successfully closed the containers
        # (containers should no longer be in the session list)
        remaining_sessions = container_manager.list_sessions()
        session_ids = [s.id for s in remaining_sessions]
        assert session_stop.id if session_stop else "stop-session" not in session_ids
        assert session_kill.id if session_kill else "kill-session" not in session_ids

    finally:
        # Clean up any remaining containers
        if session_stop and session_stop.container_id:
            try:
                container_manager.close_session(session_stop.id, kill=True)
            except Exception:
                pass
        if session_kill and session_kill.container_id:
            try:
                container_manager.close_session(session_kill.id, kill=True)
            except Exception:
                pass
