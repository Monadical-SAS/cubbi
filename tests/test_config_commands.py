"""
Tests for the configuration management commands.
"""

from cubbi.cli import app


def test_config_list(cli_runner, patched_config_manager):
    """Test the 'cubbi config list' command."""
    result = cli_runner.invoke(app, ["config", "list"])

    assert result.exit_code == 0
    assert "Configuration" in result.stdout
    assert "Value" in result.stdout

    # Check for default configurations
    assert "defaults.image" in result.stdout
    assert "defaults.connect" in result.stdout
    assert "defaults.mount_local" in result.stdout


def test_config_get(cli_runner, patched_config_manager):
    """Test the 'cubbi config get' command."""
    # Test getting an existing value
    result = cli_runner.invoke(app, ["config", "get", "defaults.image"])

    assert result.exit_code == 0
    assert "defaults.image" in result.stdout
    assert "goose" in result.stdout

    # Test getting a non-existent value
    result = cli_runner.invoke(app, ["config", "get", "nonexistent.key"])

    assert result.exit_code == 0
    assert "not found" in result.stdout


def test_config_set(cli_runner, patched_config_manager):
    """Test the 'cubbi config set' command."""
    # Test setting a string value
    result = cli_runner.invoke(app, ["config", "set", "defaults.image", "claude"])

    assert result.exit_code == 0
    assert "Configuration updated" in result.stdout
    assert patched_config_manager.get("defaults.image") == "claude"

    # Test setting a boolean value
    result = cli_runner.invoke(app, ["config", "set", "defaults.connect", "false"])

    assert result.exit_code == 0
    assert "Configuration updated" in result.stdout
    assert patched_config_manager.get("defaults.connect") is False

    # Test setting a new value
    result = cli_runner.invoke(app, ["config", "set", "new.setting", "value"])

    assert result.exit_code == 0
    assert "Configuration updated" in result.stdout
    assert patched_config_manager.get("new.setting") == "value"


def test_volume_list_empty(cli_runner, patched_config_manager):
    """Test the 'cubbi config volume list' command with no volumes."""
    result = cli_runner.invoke(app, ["config", "volume", "list"])

    assert result.exit_code == 0
    assert "No default volumes configured" in result.stdout


def test_volume_add_and_list(cli_runner, patched_config_manager, temp_config_dir):
    """Test adding a volume and then listing it."""
    # Create a test directory
    test_dir = temp_config_dir / "test_dir"
    test_dir.mkdir()

    # Add a volume
    result = cli_runner.invoke(
        app, ["config", "volume", "add", f"{test_dir}:/container/path"]
    )

    assert result.exit_code == 0
    assert "Added volume" in result.stdout

    # Verify volume was added to the configuration
    volumes = patched_config_manager.get("defaults.volumes", [])
    assert f"{test_dir}:/container/path" in volumes

    # List volumes - just check the command runs without error
    result = cli_runner.invoke(app, ["config", "volume", "list"])
    assert result.exit_code == 0
    assert "/container/path" in result.stdout


def test_volume_remove(cli_runner, patched_config_manager, temp_config_dir):
    """Test removing a volume."""
    # Create a test directory
    test_dir = temp_config_dir / "test_dir"
    test_dir.mkdir()

    # Add a volume
    patched_config_manager.set("defaults.volumes", [f"{test_dir}:/container/path"])

    # Remove the volume
    result = cli_runner.invoke(app, ["config", "volume", "remove", f"{test_dir}"])

    assert result.exit_code == 0
    assert "Removed volume" in result.stdout

    # Verify it's gone
    volumes = patched_config_manager.get("defaults.volumes")
    assert len(volumes) == 0


def test_volume_add_nonexistent_path(cli_runner, patched_config_manager, monkeypatch):
    """Test adding a volume with a nonexistent path."""
    nonexistent_path = "/path/that/does/not/exist"

    # Mock typer.confirm to return True
    monkeypatch.setattr("typer.confirm", lambda message: True)

    # Add a volume with nonexistent path
    result = cli_runner.invoke(
        app, ["config", "volume", "add", f"{nonexistent_path}:/container/path"]
    )

    assert result.exit_code == 0
    assert "Warning: Local path" in result.stdout
    assert "Added volume" in result.stdout

    # Verify it was added
    volumes = patched_config_manager.get("defaults.volumes")
    assert f"{nonexistent_path}:/container/path" in volumes


def test_network_list_empty(cli_runner, patched_config_manager):
    """Test the 'cubbi config network list' command with no networks."""
    result = cli_runner.invoke(app, ["config", "network", "list"])

    assert result.exit_code == 0
    assert "No default networks configured" in result.stdout


def test_network_add_and_list(cli_runner, patched_config_manager):
    """Test adding a network and then listing it."""
    # Add a network
    result = cli_runner.invoke(app, ["config", "network", "add", "test-network"])

    assert result.exit_code == 0
    assert "Added network" in result.stdout

    # List networks
    result = cli_runner.invoke(app, ["config", "network", "list"])

    assert result.exit_code == 0
    assert "test-network" in result.stdout


def test_network_remove(cli_runner, patched_config_manager):
    """Test removing a network."""
    # Add a network
    patched_config_manager.set("defaults.networks", ["test-network"])

    # Remove the network
    result = cli_runner.invoke(app, ["config", "network", "remove", "test-network"])

    assert result.exit_code == 0
    assert "Removed network" in result.stdout

    # Verify it's gone
    networks = patched_config_manager.get("defaults.networks")
    assert len(networks) == 0


def test_config_reset(cli_runner, patched_config_manager, monkeypatch):
    """Test resetting the configuration."""
    # Set a custom value first
    patched_config_manager.set("defaults.image", "custom-image")

    # Mock typer.confirm to return True
    monkeypatch.setattr("typer.confirm", lambda message: True)

    # Reset config
    result = cli_runner.invoke(app, ["config", "reset"])

    assert result.exit_code == 0
    assert "Configuration reset to defaults" in result.stdout

    # Verify it was reset
    assert patched_config_manager.get("defaults.image") == "goose"


# patched_config_manager fixture is now in conftest.py
