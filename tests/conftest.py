"""
Common test fixtures for Cubbi Container tests.
"""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import docker
import pytest

from cubbi.config import ConfigManager
from cubbi.container import ContainerManager
from cubbi.models import Session, SessionStatus
from cubbi.session import SessionManager
from cubbi.user_config import UserConfigManager


# Check if Docker is available
def is_docker_available():
    """Check if Docker is available and running."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


# Register custom mark for Docker-dependent tests
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_docker: mark test that requires Docker to be running"
    )


# Decorator to mark tests that require Docker
requires_docker = pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker is not available or not running",
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_container_manager(isolate_cubbi_config):
    """Mock the ContainerManager class with proper behaviors for testing."""
    mock_session = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        ports={8080: 32768},
    )

    container_manager = isolate_cubbi_config["container_manager"]

    # Patch the container manager methods for mocking
    with (
        patch.object(container_manager, "list_sessions", return_value=[]),
        patch.object(container_manager, "create_session", return_value=mock_session),
        patch.object(container_manager, "close_session", return_value=True),
        patch.object(container_manager, "close_all_sessions", return_value=(3, True)),
    ):
        yield container_manager


@pytest.fixture
def cli_runner():
    """Provide a CLI runner for testing commands."""
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture
def test_file_content(temp_config_dir):
    """Create a test file with content in a temporary directory."""
    test_content = "This is a test file for volume mounting"
    test_file = temp_config_dir / "test_volume_file.txt"
    with open(test_file, "w") as f:
        f.write(test_content)
    return test_file, test_content


@pytest.fixture
def docker_test_network():
    """Create a Docker network for testing and clean it up after."""
    if not is_docker_available():
        pytest.skip("Docker is not available")
        return None

    test_network_name = f"cubbi-test-network-{uuid.uuid4().hex[:8]}"
    client = docker.from_env()
    network = client.networks.create(test_network_name, driver="bridge")

    yield test_network_name

    # Clean up
    try:
        network.remove()
    except Exception:
        # Network might be in use by other containers
        pass


@pytest.fixture(autouse=True, scope="function")
def isolate_cubbi_config(temp_config_dir):
    """
    Automatically isolate all Cubbi configuration for every test.

    This fixture ensures that tests never touch the user's real configuration
    by patching both ConfigManager and UserConfigManager in cli.py to use
    temporary directories.
    """
    # Create isolated config instances with temporary paths
    config_path = temp_config_dir / "config.yaml"
    user_config_path = temp_config_dir / "user_config.yaml"

    # Create the ConfigManager with a custom config path
    isolated_config_manager = ConfigManager(config_path)

    # Create the UserConfigManager with a custom config path
    isolated_user_config = UserConfigManager(str(user_config_path))

    # Create isolated session manager
    sessions_path = temp_config_dir / "sessions.yaml"
    isolated_session_manager = SessionManager(sessions_path)

    # Create isolated container manager
    isolated_container_manager = ContainerManager(
        isolated_config_manager, isolated_session_manager, isolated_user_config
    )

    # Patch all the global instances in cli.py and the UserConfigManager class
    with (
        patch("cubbi.cli.config_manager", isolated_config_manager),
        patch("cubbi.cli.user_config", isolated_user_config),
        patch("cubbi.cli.session_manager", isolated_session_manager),
        patch("cubbi.cli.container_manager", isolated_container_manager),
        patch("cubbi.cli.UserConfigManager", return_value=isolated_user_config),
    ):
        # Create isolated MCP manager with isolated user config
        from cubbi.mcp import MCPManager

        isolated_mcp_manager = MCPManager(config_manager=isolated_user_config)

        # Patch the global mcp_manager instance
        with patch("cubbi.cli.mcp_manager", isolated_mcp_manager):
            yield {
                "config_manager": isolated_config_manager,
                "user_config": isolated_user_config,
                "session_manager": isolated_session_manager,
                "container_manager": isolated_container_manager,
                "mcp_manager": isolated_mcp_manager,
            }


@pytest.fixture
def patched_config_manager(isolate_cubbi_config):
    """Compatibility fixture - returns the isolated user config."""
    return isolate_cubbi_config["user_config"]
