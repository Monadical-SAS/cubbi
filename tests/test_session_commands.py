"""
Tests for the session management commands.
"""

from unittest.mock import patch


from cubbi.cli import app


def test_session_list_empty(cli_runner, mock_container_manager):
    """Test 'cubbi session list' with no active sessions."""
    mock_container_manager.list_sessions.return_value = []

    result = cli_runner.invoke(app, ["session", "list"])

    assert result.exit_code == 0
    assert "No active sessions found" in result.stdout


def test_session_list_with_sessions(cli_runner, mock_container_manager):
    """Test 'cubbi session list' with active sessions."""
    # Create a mock session and set list_sessions to return it
    from cubbi.models import Session, SessionStatus

    mock_session = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        ports={"8080": "8080"},
    )
    mock_container_manager.list_sessions.return_value = [mock_session]

    result = cli_runner.invoke(app, ["session", "list"])

    assert result.exit_code == 0
    # The output display can vary depending on terminal width, so just check
    # that the command executed successfully


def test_session_create_basic(cli_runner, mock_container_manager):
    """Test 'cubbi session create' with basic options."""
    # We need to patch user_config.get with a side_effect to handle different keys
    with patch("cubbi.cli.user_config") as mock_user_config:
        # Handle different key requests appropriately
        def mock_get_side_effect(key, default=None):
            if key == "defaults.image":
                return "goose"
            elif key == "defaults.volumes":
                return []  # Return empty list for volumes
            elif key == "defaults.connect":
                return True
            elif key == "defaults.mount_local":
                return True
            elif key == "defaults.networks":
                return []
            return default

        mock_user_config.get.side_effect = mock_get_side_effect
        mock_user_config.get_environment_variables.return_value = {}

        result = cli_runner.invoke(app, ["session", "create"])

        if result.exit_code != 0:
            print(f"Error: {result.exception}")

        assert result.exit_code == 0
        assert "Session created successfully" in result.stdout

        # Verify container_manager was called with the expected image
        mock_container_manager.create_session.assert_called_once()
        assert (
            mock_container_manager.create_session.call_args[1]["image_name"] == "goose"
        )


def test_session_close(cli_runner, mock_container_manager):
    """Test 'cubbi session close' command."""
    mock_container_manager.close_session.return_value = True

    result = cli_runner.invoke(app, ["session", "close", "test-session-id"])

    assert result.exit_code == 0
    assert "closed successfully" in result.stdout
    mock_container_manager.close_session.assert_called_once_with(
        "test-session-id", kill=False
    )


def test_session_close_all(cli_runner, mock_container_manager):
    """Test 'cubbi session close --all' command."""
    # Set up mock sessions
    from cubbi.models import Session, SessionStatus

    # timestamp no longer needed since we don't use created_at in Session
    mock_sessions = [
        Session(
            id=f"session-{i}",
            name=f"Session {i}",
            image="goose",
            status=SessionStatus.RUNNING,
            ports={},
        )
        for i in range(3)
    ]

    mock_container_manager.list_sessions.return_value = mock_sessions
    mock_container_manager.close_all_sessions.return_value = (3, True)

    result = cli_runner.invoke(app, ["session", "close", "--all"])

    assert result.exit_code == 0
    assert "3 sessions closed successfully" in result.stdout
    mock_container_manager.close_all_sessions.assert_called_once()


def test_session_create_with_ports(
    cli_runner, mock_container_manager, patched_config_manager
):
    """Test session creation with port forwarding."""
    from cubbi.models import Session, SessionStatus

    # Mock the create_session to return a session with ports
    mock_session = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        ports={8000: 32768, 3000: 32769},
    )
    mock_container_manager.create_session.return_value = mock_session

    result = cli_runner.invoke(app, ["session", "create", "--port", "8000,3000"])

    assert result.exit_code == 0
    assert "Session created successfully" in result.stdout
    assert "Forwarding ports: 8000, 3000" in result.stdout

    # Verify create_session was called with correct ports
    mock_container_manager.create_session.assert_called_once()
    call_args = mock_container_manager.create_session.call_args
    assert call_args.kwargs["ports"] == [8000, 3000]


def test_session_create_with_default_ports(
    cli_runner, mock_container_manager, patched_config_manager
):
    """Test session creation using default ports."""
    from cubbi.models import Session, SessionStatus

    # Set up default ports
    patched_config_manager.set("defaults.ports", [8080, 9000])

    # Mock the create_session to return a session with ports
    mock_session = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        ports={8080: 32768, 9000: 32769},
    )
    mock_container_manager.create_session.return_value = mock_session

    result = cli_runner.invoke(app, ["session", "create"])

    assert result.exit_code == 0
    assert "Session created successfully" in result.stdout
    assert "Forwarding ports: 8080, 9000" in result.stdout

    # Verify create_session was called with default ports
    mock_container_manager.create_session.assert_called_once()
    call_args = mock_container_manager.create_session.call_args
    assert call_args.kwargs["ports"] == [8080, 9000]


def test_session_create_combine_default_and_custom_ports(
    cli_runner, mock_container_manager, patched_config_manager
):
    """Test session creation combining default and custom ports."""
    from cubbi.models import Session, SessionStatus

    # Set up default ports
    patched_config_manager.set("defaults.ports", [8080])

    # Mock the create_session to return a session with combined ports
    mock_session = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        ports={8080: 32768, 3000: 32769},
    )
    mock_container_manager.create_session.return_value = mock_session

    result = cli_runner.invoke(app, ["session", "create", "--port", "3000"])

    assert result.exit_code == 0
    assert "Session created successfully" in result.stdout
    # Ports should be combined and deduplicated
    assert "Forwarding ports:" in result.stdout

    # Verify create_session was called with combined ports
    mock_container_manager.create_session.assert_called_once()
    call_args = mock_container_manager.create_session.call_args
    # Should contain both default (8080) and custom (3000) ports
    assert set(call_args.kwargs["ports"]) == {8080, 3000}


def test_session_create_invalid_port_format(
    cli_runner, mock_container_manager, patched_config_manager
):
    """Test session creation with invalid port format."""
    result = cli_runner.invoke(app, ["session", "create", "--port", "invalid"])

    assert result.exit_code == 0
    assert "Warning: Ignoring invalid port format" in result.stdout

    # Session creation should continue with empty ports list (invalid port ignored)
    mock_container_manager.create_session.assert_called_once()
    call_args = mock_container_manager.create_session.call_args
    assert call_args.kwargs["ports"] == []  # Invalid port should be ignored


def test_session_create_invalid_port_range(
    cli_runner, mock_container_manager, patched_config_manager
):
    """Test session creation with port outside valid range."""
    result = cli_runner.invoke(app, ["session", "create", "--port", "70000"])

    assert result.exit_code == 0
    assert "Error: Invalid ports [70000]" in result.stdout

    # Session creation should not happen due to early return
    mock_container_manager.create_session.assert_not_called()


def test_session_list_shows_ports(cli_runner, mock_container_manager):
    """Test that session list shows port mappings."""
    from cubbi.models import Session, SessionStatus

    mock_session = Session(
        id="test-session-id",
        name="test-session",
        image="goose",
        status=SessionStatus.RUNNING,
        ports={8000: 32768, 3000: 32769},
    )
    mock_container_manager.list_sessions.return_value = [mock_session]

    result = cli_runner.invoke(app, ["session", "list"])

    assert result.exit_code == 0
    assert "8000:32768" in result.stdout
    assert "3000:32769" in result.stdout


def test_session_close_with_kill_flag(
    cli_runner, mock_container_manager, patched_config_manager
):
    """Test session close with --kill flag."""
    result = cli_runner.invoke(app, ["session", "close", "test-session-id", "--kill"])

    assert result.exit_code == 0

    # Verify close_session was called with kill=True
    mock_container_manager.close_session.assert_called_once_with(
        "test-session-id", kill=True
    )


def test_session_close_all_with_kill_flag(
    cli_runner, mock_container_manager, patched_config_manager
):
    """Test session close --all with --kill flag."""
    from cubbi.models import Session, SessionStatus

    # Mock some sessions to close
    mock_sessions = [
        Session(
            id="session-1",
            name="Session 1",
            image="goose",
            status=SessionStatus.RUNNING,
            ports={},
        ),
        Session(
            id="session-2",
            name="Session 2",
            image="goose",
            status=SessionStatus.RUNNING,
            ports={},
        ),
    ]
    mock_container_manager.list_sessions.return_value = mock_sessions
    mock_container_manager.close_all_sessions.return_value = (2, True)

    result = cli_runner.invoke(app, ["session", "close", "--all", "--kill"])

    assert result.exit_code == 0
    assert "2 sessions closed successfully" in result.stdout

    # Verify close_all_sessions was called with kill=True
    mock_container_manager.close_all_sessions.assert_called_once()
    call_args = mock_container_manager.close_all_sessions.call_args
    assert call_args.kwargs["kill"] is True


# For more complex tests that need actual Docker,
# we've implemented them in test_integration_docker.py
# They will run automatically if Docker is available
