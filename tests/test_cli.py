from typer.testing import CliRunner

from cubbi.cli import app

runner = CliRunner()


def test_version() -> None:
    """Test version command"""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Cubbi - Cubbi Container Tool" in result.stdout


def test_session_list() -> None:
    """Test session list command"""
    result = runner.invoke(app, ["session", "list"])
    assert result.exit_code == 0
    # Could be either "No active sessions found" or a table with headers
    assert "no active" in result.stdout.lower() or "id" in result.stdout.lower()


def test_help() -> None:
    """Test help command"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "Cubbi Container Tool" in result.stdout
