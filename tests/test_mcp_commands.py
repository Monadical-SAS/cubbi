"""
Tests for the MCP server management commands.
"""

import pytest
from unittest.mock import patch
from mcontainer.cli import app


def test_mcp_list_empty(cli_runner, patched_config_manager):
    """Test the 'mc mcp list' command with no MCPs configured."""
    # Make sure mcps is empty
    patched_config_manager.set("mcps", [])

    with patch("mcontainer.cli.mcp_manager.list_mcps") as mock_list_mcps:
        mock_list_mcps.return_value = []

        result = cli_runner.invoke(app, ["mcp", "list"])

        assert result.exit_code == 0
        assert "No MCP servers configured" in result.stdout


def test_mcp_remote_add_and_list(cli_runner, patched_config_manager):
    """Test adding a remote MCP server and listing it."""
    # Add a remote MCP server
    result = cli_runner.invoke(
        app,
        [
            "mcp",
            "remote",
            "add",
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
    assert "http://mcp-server.example.com" in result.stdout


def test_mcp_docker_add_and_list(cli_runner, patched_config_manager):
    """Test adding a Docker-based MCP server and listing it."""
    # Add a Docker MCP server
    result = cli_runner.invoke(
        app,
        [
            "mcp",
            "docker",
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
    assert "Added Docker-based MCP server" in result.stdout

    # List MCP servers
    result = cli_runner.invoke(app, ["mcp", "list"])

    assert result.exit_code == 0
    assert "test-docker-mcp" in result.stdout
    assert "docker" in result.stdout
    assert "mcp/github:latest" in result.stdout


def test_mcp_proxy_add_and_list(cli_runner, patched_config_manager):
    """Test adding a proxy-based MCP server and listing it."""
    # Add a proxy MCP server
    result = cli_runner.invoke(
        app,
        [
            "mcp",
            "proxy",
            "add",
            "test-proxy-mcp",
            "ghcr.io/mcp/github:latest",
            "--proxy-image",
            "ghcr.io/sparfenyuk/mcp-proxy:latest",
            "--command",
            "github-mcp",
            "--sse-port",
            "8080",
            "--sse-host",
            "0.0.0.0",
            "--allow-origin",
            "*",
            "--env",
            "GITHUB_TOKEN=test-token",
        ],
    )

    assert result.exit_code == 0
    assert "Added proxy-based MCP server" in result.stdout

    # List MCP servers
    result = cli_runner.invoke(app, ["mcp", "list"])

    assert result.exit_code == 0
    assert "test-proxy-mcp" in result.stdout
    assert "proxy" in result.stdout
    assert (
        "ghcr.io/mcp/github" in result.stdout
    )  # Partial match due to potential truncation
    # The proxy image might not be visible in the table output
    # so we'll check for the specific format we expect instead
    assert "via" in result.stdout


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

    # Mock the get_mcp and remove_mcp methods
    with patch("mcontainer.cli.mcp_manager.get_mcp") as mock_get_mcp:
        # First make get_mcp return our MCP
        mock_get_mcp.return_value = {
            "name": "test-mcp",
            "type": "remote",
            "url": "http://test-server.com/sse",
            "headers": {"Authorization": "Bearer test-token"},
        }

        # Mock the remove_mcp method to return True
        with patch("mcontainer.cli.mcp_manager.remove_mcp") as mock_remove_mcp:
            mock_remove_mcp.return_value = True

            # Remove the MCP server
            result = cli_runner.invoke(app, ["mcp", "remove", "test-mcp"])

            assert result.exit_code == 0
            assert "Removed MCP server" in result.stdout

            # Verify remove_mcp was called with the right name
            mock_remove_mcp.assert_called_once_with("test-mcp")


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
    with patch("mcontainer.cli.mcp_manager.get_mcp") as mock_get_mcp:
        mock_get_mcp.return_value = {
            "name": "test-docker-mcp",
            "type": "docker",
            "image": "mcp/test:latest",
            "command": "test-command",
            "env": {"TEST_ENV": "test-value"},
        }

        # Then mock the get_mcp_status method
        with patch("mcontainer.cli.mcp_manager.get_mcp_status") as mock_get_status:
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
def test_mcp_start(cli_runner, patched_config_manager, mock_container_manager):
    """Test starting an MCP server."""
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

    # Mock the start operation
    mock_container_manager.start_mcp.return_value = {
        "container_id": "test-container-id",
        "status": "running",
    }

    # Start the MCP
    result = cli_runner.invoke(app, ["mcp", "start", "test-docker-mcp"])

    assert result.exit_code == 0
    assert "Started MCP server" in result.stdout
    assert "test-docker-mcp" in result.stdout


@pytest.mark.requires_docker
def test_mcp_stop(cli_runner, patched_config_manager, mock_container_manager):
    """Test stopping an MCP server."""
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

    # Mock the stop operation
    mock_container_manager.stop_mcp.return_value = True

    # Stop the MCP
    result = cli_runner.invoke(app, ["mcp", "stop", "test-docker-mcp"])

    assert result.exit_code == 0
    assert "Stopped MCP server" in result.stdout
    assert "test-docker-mcp" in result.stdout


@pytest.mark.requires_docker
def test_mcp_restart(cli_runner, patched_config_manager, mock_container_manager):
    """Test restarting an MCP server."""
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

    # Mock the restart operation
    mock_container_manager.restart_mcp.return_value = {
        "container_id": "test-container-id",
        "status": "running",
    }

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
    with patch("mcontainer.cli.mcp_manager.get_mcp_logs") as mock_get_logs:
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
    from mcontainer.models import Session, SessionStatus

    timestamp = "2023-01-01T00:00:00Z"
    mock_container_manager.create_session.return_value = Session(
        id="test-session-id",
        name="test-session",
        driver="goose",
        status=SessionStatus.RUNNING,
        container_id="test-container-id",
        created_at=timestamp,
        ports={},
        mcps=["test-mcp"],
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
