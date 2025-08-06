"""
Tests for the MCP server management commands.
"""

import pytest
from unittest.mock import patch
from cubbi.cli import app


def test_mcp_list_empty(cli_runner, patched_config_manager):
    """Test the 'cubbi mcp list' command with no MCPs configured."""
    # Make sure mcps is empty
    patched_config_manager.set("mcps", [])

    with patch("cubbi.cli.mcp_manager.list_mcps") as mock_list_mcps:
        mock_list_mcps.return_value = []

        result = cli_runner.invoke(app, ["mcp", "list"])

        assert result.exit_code == 0
        assert "No MCP servers configured" in result.stdout


def test_mcp_add_remote(cli_runner, isolate_cubbi_config):
    """Test adding a remote MCP server and listing it."""
    # Add a remote MCP server
    result = cli_runner.invoke(
        app,
        [
            "mcp",
            "add-remote",
            "test-remote-mcp",
            "http://mcp-server.example.com/sse",
            "--header",
            "Authorization=Bearer test-token",
        ],
    )

    assert result.exit_code == 0
    assert "Added remote MCP server" in result.stdout

    # List MCP servers
    result = cli_runner.invoke(app, ["mcp", "list"])

    assert result.exit_code == 0
    assert "test-remote-mcp" in result.stdout
    assert "remote" in result.stdout
    # Check partial URL since it may be truncated in the table display
    assert "http://mcp-se" in result.stdout  # Truncated in table view


def test_mcp_add(cli_runner, isolate_cubbi_config):
    """Test adding a proxy-based MCP server and listing it."""
    # Add a Docker MCP server
    result = cli_runner.invoke(
        app,
        [
            "mcp",
            "add",
            "test-docker-mcp",
            "mcp/github:latest",
            "--command",
            "github-mcp",
            "--env",
            "GITHUB_TOKEN=test-token",
        ],
    )

    assert result.exit_code == 0
    assert "Added MCP server" in result.stdout

    # List MCP servers
    result = cli_runner.invoke(app, ["mcp", "list"])

    assert result.exit_code == 0
    assert "test-docker-mcp" in result.stdout
    assert "proxy" in result.stdout  # It's a proxy-based MCP
    assert "mcp/github:la" in result.stdout  # Truncated in table view


def test_mcp_remove(cli_runner, patched_config_manager):
    """Test removing an MCP server."""
    # Add a remote MCP server
    patched_config_manager.set(
        "mcps",
        [
            {
                "name": "test-mcp",
                "type": "remote",
                "url": "http://test-server.com/sse",
                "headers": {"Authorization": "Bearer test-token"},
            }
        ],
    )

    # Mock the container_manager.list_sessions to return sessions without MCPs
    with patch("cubbi.cli.container_manager.list_sessions") as mock_list_sessions:
        mock_list_sessions.return_value = []

        # Mock the remove_mcp method
        with patch("cubbi.cli.mcp_manager.remove_mcp") as mock_remove_mcp:
            # Make remove_mcp return True (successful removal)
            mock_remove_mcp.return_value = True

            # Remove the MCP server
            result = cli_runner.invoke(app, ["mcp", "remove", "test-mcp"])

            # Just check it ran successfully with exit code 0
            assert result.exit_code == 0
            assert "Removed MCP server 'test-mcp'" in result.stdout


def test_mcp_remove_with_active_sessions(cli_runner, patched_config_manager):
    """Test removing an MCP server that is used by active sessions."""
    from cubbi.models import Session, SessionStatus

    # Add a remote MCP server
    patched_config_manager.set(
        "mcps",
        [
            {
                "name": "test-mcp",
                "type": "remote",
                "url": "http://test-server.com/sse",
                "headers": {"Authorization": "Bearer test-token"},
            }
        ],
    )

    # Create mock sessions that use the MCP
    mock_sessions = [
        Session(
            id="session-1",
            name="test-session-1",
            image="goose",
            status=SessionStatus.RUNNING,
            container_id="container-1",
            mcps=["test-mcp", "other-mcp"],
        ),
        Session(
            id="session-2",
            name="test-session-2",
            image="goose",
            status=SessionStatus.RUNNING,
            container_id="container-2",
            mcps=["other-mcp"],  # This one doesn't use test-mcp
        ),
        Session(
            id="session-3",
            name="test-session-3",
            image="goose",
            status=SessionStatus.RUNNING,
            container_id="container-3",
            mcps=["test-mcp"],  # This one uses test-mcp
        ),
    ]

    # Mock the container_manager.list_sessions to return our sessions
    with patch("cubbi.cli.container_manager.list_sessions") as mock_list_sessions:
        mock_list_sessions.return_value = mock_sessions

        # Mock the remove_mcp method
        with patch("cubbi.cli.mcp_manager.remove_mcp") as mock_remove_mcp:
            # Make remove_mcp return True (successful removal)
            mock_remove_mcp.return_value = True

            # Remove the MCP server
            result = cli_runner.invoke(app, ["mcp", "remove", "test-mcp"])

            # Check it ran successfully with exit code 0
            assert result.exit_code == 0
            assert "Removed MCP server 'test-mcp'" in result.stdout
            # Check warning about affected sessions
            assert (
                "Warning: Found 2 active sessions using MCP 'test-mcp'" in result.stdout
            )
            assert "session-1" in result.stdout
            assert "session-3" in result.stdout
            # session-2 should not be mentioned since it doesn't use test-mcp
            assert "session-2" not in result.stdout


def test_mcp_remove_nonexistent(cli_runner, patched_config_manager):
    """Test removing a non-existent MCP server."""
    # No MCPs configured
    patched_config_manager.set("mcps", [])

    # Mock the container_manager.list_sessions to return empty list
    with patch("cubbi.cli.container_manager.list_sessions") as mock_list_sessions:
        mock_list_sessions.return_value = []

        # Mock the remove_mcp method to return False (MCP not found)
        with patch("cubbi.cli.mcp_manager.remove_mcp") as mock_remove_mcp:
            mock_remove_mcp.return_value = False

            # Try to remove a non-existent MCP server
            result = cli_runner.invoke(app, ["mcp", "remove", "nonexistent-mcp"])

            # Check it ran successfully but reported not found
            assert result.exit_code == 0
            assert "MCP server 'nonexistent-mcp' not found" in result.stdout


def test_session_mcps_attribute():
    """Test that Session model has mcps attribute and can be populated correctly."""
    from cubbi.models import Session, SessionStatus

    # Test that Session can be created with mcps attribute
    session = Session(
        id="test-session",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        container_id="test-container",
        mcps=["mcp1", "mcp2"],
    )

    assert session.mcps == ["mcp1", "mcp2"]

    # Test that Session can be created with empty mcps list
    session_empty = Session(
        id="test-session-2",
        name="test-session-2",
        image="goose",
        status=SessionStatus.RUNNING,
        container_id="test-container-2",
    )

    assert session_empty.mcps == []  # Should default to empty list


def test_session_mcps_from_container_labels():
    """Test that Session mcps are correctly populated from container labels."""
    from unittest.mock import Mock
    from cubbi.container import ContainerManager

    # Mock a container with MCP labels
    mock_container = Mock()
    mock_container.id = "test-container-id"
    mock_container.status = "running"
    mock_container.labels = {
        "cubbi.session": "true",
        "cubbi.session.id": "test-session",
        "cubbi.session.name": "test-session-name",
        "cubbi.image": "goose",
        "cubbi.mcps": "mcp1,mcp2,mcp3",  # Test with multiple MCPs
    }
    mock_container.attrs = {"NetworkSettings": {"Ports": {}}}

    # Mock Docker client
    mock_client = Mock()
    mock_client.containers.list.return_value = [mock_container]

    # Create container manager with mocked client
    with patch("cubbi.container.docker.from_env") as mock_docker:
        mock_docker.return_value = mock_client
        mock_client.ping.return_value = True

        container_manager = ContainerManager()
        sessions = container_manager.list_sessions()

        assert len(sessions) == 1
        session = sessions[0]
        assert session.id == "test-session"
        assert session.mcps == ["mcp1", "mcp2", "mcp3"]


def test_session_mcps_from_empty_container_labels():
    """Test that Session mcps are correctly handled when container has no MCP labels."""
    from unittest.mock import Mock
    from cubbi.container import ContainerManager

    # Mock a container without MCP labels
    mock_container = Mock()
    mock_container.id = "test-container-id"
    mock_container.status = "running"
    mock_container.labels = {
        "cubbi.session": "true",
        "cubbi.session.id": "test-session",
        "cubbi.session.name": "test-session-name",
        "cubbi.image": "goose",
        # No cubbi.mcps label
    }
    mock_container.attrs = {"NetworkSettings": {"Ports": {}}}

    # Mock Docker client
    mock_client = Mock()
    mock_client.containers.list.return_value = [mock_container]

    # Create container manager with mocked client
    with patch("cubbi.container.docker.from_env") as mock_docker:
        mock_docker.return_value = mock_client
        mock_client.ping.return_value = True

        container_manager = ContainerManager()
        sessions = container_manager.list_sessions()

        assert len(sessions) == 1
        session = sessions[0]
        assert session.id == "test-session"
        assert session.mcps == []  # Should be empty list when no MCPs


@pytest.mark.requires_docker
def test_mcp_status(cli_runner, patched_config_manager, mock_container_manager):
    """Test the MCP status command."""
    # Add a Docker MCP
    patched_config_manager.set(
        "mcps",
        [
            {
                "name": "test-docker-mcp",
                "type": "docker",
                "image": "mcp/test:latest",
                "command": "test-command",
                "env": {"TEST_ENV": "test-value"},
            }
        ],
    )

    # First mock get_mcp to return our MCP config
    with patch("cubbi.cli.mcp_manager.get_mcp") as mock_get_mcp:
        mock_get_mcp.return_value = {
            "name": "test-docker-mcp",
            "type": "docker",
            "image": "mcp/test:latest",
            "command": "test-command",
            "env": {"TEST_ENV": "test-value"},
        }

        # Then mock the get_mcp_status method
        with patch("cubbi.cli.mcp_manager.get_mcp_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "running",
                "container_id": "test-container-id",
                "name": "test-docker-mcp",
                "type": "docker",
                "image": "mcp/test:latest",
                "ports": {"8080/tcp": 8080},
                "created": "2023-01-01T00:00:00Z",
            }

            # Check MCP status
            result = cli_runner.invoke(app, ["mcp", "status", "test-docker-mcp"])

            assert result.exit_code == 0
            assert "test-docker-mcp" in result.stdout
            assert "running" in result.stdout
            assert "mcp/test:latest" in result.stdout


@pytest.mark.requires_docker
def test_mcp_start(cli_runner, isolate_cubbi_config):
    """Test starting an MCP server."""
    mcp_manager = isolate_cubbi_config["mcp_manager"]

    # Add a Docker MCP
    isolate_cubbi_config["user_config"].set(
        "mcps",
        [
            {
                "name": "test-docker-mcp",
                "type": "docker",
                "image": "mcp/test:latest",
                "command": "test-command",
            }
        ],
    )

    # Mock the start_mcp method to avoid actual Docker operations
    with patch.object(
        mcp_manager,
        "start_mcp",
        return_value={
            "container_id": "test-container-id",
            "status": "running",
        },
    ):
        # Start the MCP
        result = cli_runner.invoke(app, ["mcp", "start", "test-docker-mcp"])

        assert result.exit_code == 0
        assert "Started MCP server" in result.stdout
        assert "test-docker-mcp" in result.stdout


@pytest.mark.requires_docker
def test_mcp_stop(cli_runner, isolate_cubbi_config):
    """Test stopping an MCP server."""
    mcp_manager = isolate_cubbi_config["mcp_manager"]

    # Add a Docker MCP
    isolate_cubbi_config["user_config"].set(
        "mcps",
        [
            {
                "name": "test-docker-mcp",
                "type": "docker",
                "image": "mcp/test:latest",
                "command": "test-command",
            }
        ],
    )

    # Mock the stop_mcp method to avoid actual Docker operations
    with patch.object(mcp_manager, "stop_mcp", return_value=True):
        # Stop the MCP
        result = cli_runner.invoke(app, ["mcp", "stop", "test-docker-mcp"])

        assert result.exit_code == 0
        assert "Stopped and removed MCP server" in result.stdout
        assert "test-docker-mcp" in result.stdout


@pytest.mark.requires_docker
def test_mcp_restart(cli_runner, isolate_cubbi_config):
    """Test restarting an MCP server."""
    mcp_manager = isolate_cubbi_config["mcp_manager"]

    # Add a Docker MCP
    isolate_cubbi_config["user_config"].set(
        "mcps",
        [
            {
                "name": "test-docker-mcp",
                "type": "docker",
                "image": "mcp/test:latest",
                "command": "test-command",
            }
        ],
    )

    # Mock the restart_mcp method to avoid actual Docker operations
    with patch.object(
        mcp_manager,
        "restart_mcp",
        return_value={
            "container_id": "test-container-id",
            "status": "running",
        },
    ):
        # Restart the MCP
        result = cli_runner.invoke(app, ["mcp", "restart", "test-docker-mcp"])

        assert result.exit_code == 0
        assert "Restarted MCP server" in result.stdout
        assert "test-docker-mcp" in result.stdout


@pytest.mark.requires_docker
def test_mcp_logs(cli_runner, patched_config_manager, mock_container_manager):
    """Test viewing MCP server logs."""
    # Add a Docker MCP
    patched_config_manager.set(
        "mcps",
        [
            {
                "name": "test-docker-mcp",
                "type": "docker",
                "image": "mcp/test:latest",
                "command": "test-command",
            }
        ],
    )

    # Mock the logs operation
    with patch("cubbi.cli.mcp_manager.get_mcp_logs") as mock_get_logs:
        mock_get_logs.return_value = "Test log output"

        # View MCP logs
        result = cli_runner.invoke(app, ["mcp", "logs", "test-docker-mcp"])

        assert result.exit_code == 0
        assert "Test log output" in result.stdout


def test_session_with_mcp(cli_runner, patched_config_manager, mock_container_manager):
    """Test creating a session with an MCP server attached."""
    # Add an MCP server
    patched_config_manager.set(
        "mcps",
        [
            {
                "name": "test-mcp",
                "type": "docker",
                "image": "mcp/test:latest",
                "command": "test-command",
            }
        ],
    )

    # Mock the session creation with MCP
    from cubbi.models import Session, SessionStatus

    # timestamp no longer needed since we don't use created_at in Session
    mock_container_manager.create_session.return_value = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        container_id="test-container-id",
        ports={},
    )

    # Create a session with MCP
    result = cli_runner.invoke(app, ["session", "create", "--mcp", "test-mcp"])

    assert result.exit_code == 0
    assert "Session created successfully" in result.stdout
    assert "test-session" in result.stdout
    # Check that the create_session was called with the mcp parameter
    assert mock_container_manager.create_session.called
    # The keyword arguments are in the second element of call_args
    kwargs = mock_container_manager.create_session.call_args[1]
    assert "mcp" in kwargs
    assert "test-mcp" in kwargs["mcp"]
