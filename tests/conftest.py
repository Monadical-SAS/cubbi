"""
Common test fixtures for Cubbi Container tests.
"""

import uuid
import tempfile
import pytest
import docker
from pathlib import Path
from unittest.mock import patch

from cubbi.container import ContainerManager
from cubbi.session import SessionManager
from cubbi.config import ConfigManager
from cubbi.models import Session, SessionStatus
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
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def isolated_config(temp_config_dir):
    """Provide an isolated UserConfigManager instance."""
    config_path = temp_config_dir / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return UserConfigManager(str(config_path))


@pytest.fixture
def isolated_session_manager(temp_config_dir):
    """Create an isolated session manager for testing."""
    sessions_path = temp_config_dir / "sessions.yaml"
    return SessionManager(sessions_path)


@pytest.fixture
def isolated_config_manager():
    """Create an isolated config manager for testing."""
    config_manager = ConfigManager()
    # Ensure we're using the built-in images, not trying to load from user config
    return config_manager


@pytest.fixture
def mock_session_manager():
    """Mock the SessionManager class."""
    with patch("cubbi.cli.session_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_container_manager():
    """Mock the ContainerManager class with proper initialization."""
    mock_session = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        ports={"8080": "8080"},
    )

    with patch("cubbi.cli.container_manager") as mock_manager:
        # Set behaviors to avoid TypeErrors
        mock_manager.list_sessions.return_value = []
        mock_manager.create_session.return_value = mock_session
        mock_manager.close_session.return_value = True
        mock_manager.close_all_sessions.return_value = (3, True)
        # MCP-related mocks
        mock_manager.get_mcp_status.return_value = {
            "status": "running",
            "container_id": "test-id",
        }
        mock_manager.start_mcp.return_value = {
            "status": "running",
            "container_id": "test-id",
        }
        mock_manager.stop_mcp.return_value = True
        mock_manager.restart_mcp.return_value = {
            "status": "running",
            "container_id": "test-id",
        }
        mock_manager.get_mcp_logs.return_value = "Test log output"
        yield mock_manager


@pytest.fixture
def container_manager(isolated_session_manager, isolated_config_manager):
    """Create a container manager with isolated components."""
    return ContainerManager(
        config_manager=isolated_config_manager, session_manager=isolated_session_manager
    )


@pytest.fixture
def cli_runner():
    """Provide a CLI runner for testing commands."""
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture
def test_file_content(temp_dir):
    """Create a test file with content in the temporary directory."""
    test_content = "This is a test file for volume mounting"
    test_file = temp_dir / "test_volume_file.txt"
    with open(test_file, "w") as f:
        f.write(test_content)
    return test_file, test_content


@pytest.fixture
def test_network_name():
    """Generate a unique network name for testing."""
    return f"cubbi-test-network-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def docker_test_network(test_network_name):
    """Create a Docker network for testing and clean it up after."""
    if not is_docker_available():
        pytest.skip("Docker is not available")
        return None

    client = docker.from_env()
    network = client.networks.create(test_network_name, driver="bridge")

    yield test_network_name

    # Clean up
    try:
        network.remove()
    except Exception:
        # Network might be in use by other containers
        pass


@pytest.fixture
def patched_config_manager(isolated_config):
    """Patch the UserConfigManager in cli.py to use our isolated instance."""
    with patch("cubbi.cli.user_config", isolated_config):
        yield isolated_config
