from typer.testing import CliRunner
from mcontainer.cli import app

runner = CliRunner()


def test_version() -> None:
    """Test version command"""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "MC - Monadical Container Tool" in result.stdout


def test_session_list() -> None:
    """Test session list command"""
    result = runner.invoke(app, ["session", "list"])
    assert result.exit_code == 0
    # Could be either "No active sessions found" or a table of sessions
    assert "sessions" in result.stdout.lower() or "no active" in result.stdout.lower()


def test_help() -> None:
    """Test help command"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "Monadical Container Tool" in result.stdout