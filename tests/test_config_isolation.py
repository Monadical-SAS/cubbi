"""
Test that configuration isolation works correctly and doesn't touch user's real config.
"""

from pathlib import Path
from cubbi.cli import app


def test_config_isolation_preserves_user_config(cli_runner, isolate_cubbi_config):
    """Test that test isolation doesn't affect user's real configuration."""

    # Get the user's real config path
    real_config_path = Path.home() / ".config" / "cubbi" / "config.yaml"

    # If the user has a real config, store its content before test
    original_content = None
    if real_config_path.exists():
        with open(real_config_path, "r") as f:
            original_content = f.read()

    # Run some config modification commands in the test
    result = cli_runner.invoke(app, ["config", "port", "add", "9999"])
    assert result.exit_code == 0

    result = cli_runner.invoke(app, ["config", "set", "defaults.image", "test-image"])
    assert result.exit_code == 0

    # Verify the user's real config is unchanged
    if original_content is not None:
        with open(real_config_path, "r") as f:
            current_content = f.read()
        assert current_content == original_content
    else:
        # If no real config existed, it should still not exist
        assert not real_config_path.exists()


def test_isolated_config_works_independently(cli_runner, isolate_cubbi_config):
    """Test that the isolated config works correctly for tests."""

    # Add a port to isolated config
    result = cli_runner.invoke(app, ["config", "port", "add", "8888"])
    assert result.exit_code == 0
    assert "Added port 8888 to defaults" in result.stdout

    # Verify it appears in the list
    result = cli_runner.invoke(app, ["config", "port", "list"])
    assert result.exit_code == 0
    assert "8888" in result.stdout

    # Remove the port
    result = cli_runner.invoke(app, ["config", "port", "remove", "8888"])
    assert result.exit_code == 0
    assert "Removed port 8888 from defaults" in result.stdout

    # Verify it's gone
    result = cli_runner.invoke(app, ["config", "port", "list"])
    assert result.exit_code == 0
    assert "No default ports configured" in result.stdout


def test_each_test_gets_fresh_config(cli_runner, isolate_cubbi_config):
    """Test that each test gets a fresh, isolated configuration."""

    # This test should start with empty ports (fresh config)
    result = cli_runner.invoke(app, ["config", "port", "list"])
    assert result.exit_code == 0
    assert "No default ports configured" in result.stdout

    # Add a port
    result = cli_runner.invoke(app, ["config", "port", "add", "7777"])
    assert result.exit_code == 0

    # Verify it's there
    result = cli_runner.invoke(app, ["config", "port", "list"])
    assert result.exit_code == 0
    assert "7777" in result.stdout


def test_another_fresh_config_test(cli_runner, isolate_cubbi_config):
    """Another test to verify each test gets a completely fresh config."""

    # This test should also start with empty ports (independent of previous test)
    result = cli_runner.invoke(app, ["config", "port", "list"])
    assert result.exit_code == 0
    assert "No default ports configured" in result.stdout

    # The port from the previous test should not be here
    result = cli_runner.invoke(app, ["config", "port", "list"])
    assert "7777" not in result.stdout
