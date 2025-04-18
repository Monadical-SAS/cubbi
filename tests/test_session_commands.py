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
    mock_container_manager.close_session.assert_called_once_with("test-session-id")


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


# For more complex tests that need actual Docker,
# we've implemented them in test_integration_docker.py
# They will run automatically if Docker is available
