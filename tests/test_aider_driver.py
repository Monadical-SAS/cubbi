"""
Tests for the 'aider' driver in Monadical Container.
"""

import os
import pytest
import uuid
import time
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from conftest import requires_docker
from mcontainer.config import ConfigManager

# Check if we're running the Docker tests
SKIP_DOCKER_TESTS = os.environ.get("SKIP_DOCKER_TESTS", "false").lower() == "true"


def test_aider_driver_loaded():
    """Test that the aider driver is correctly loaded."""
    config_manager = ConfigManager()
    drivers = config_manager.list_drivers()
    
    # Check that aider driver exists in the available drivers
    assert "aider" in drivers, "Aider driver not found in available drivers"


def test_aider_driver_configuration():
    """Test that the aider driver configuration is correct."""
    config_manager = ConfigManager()
    driver = config_manager.get_driver("aider")
    
    assert driver is not None, "Aider driver not found"
    assert driver.name == "aider", f"Driver name is {driver.name}, expected 'aider'"
    assert driver.description == "Aider AI programming assistant environment"
    assert driver.maintainer is not None, "Maintainer not specified"
    assert driver.version is not None, "Version not specified"
    
    # Test environment variables - should at least have OpenAI API key
    env_var_names = [env.name for env in driver.environment]
    assert "OPENAI_API_KEY" in env_var_names, "OPENAI_API_KEY not in environment variables"
    
    # Should have ports for editor integration
    assert len(driver.ports) > 0, "No ports defined in driver configuration"
    
    # Should have volume mounts
    assert len(driver.volumes) > 0, "No volume mounts defined in driver configuration"
    
    # Should have persistent configuration
    assert len(driver.persistent_configs) > 0, "No persistent configurations defined"


def test_aider_driver_directory_structure():
    """Test that the aider driver directory has all required files."""
    config_manager = ConfigManager()
    driver_path = config_manager.get_driver_path("aider")
    
    assert driver_path is not None, "Aider driver path not found"
    assert driver_path.exists(), f"Driver path {driver_path} does not exist"
    
    # Check for required files
    assert (driver_path / "mc-driver.yaml").exists(), "mc-driver.yaml not found"
    assert (driver_path / "Dockerfile").exists(), "Dockerfile not found"
    assert (driver_path / "entrypoint.sh").exists(), "entrypoint.sh not found"
    assert (driver_path / "mc-init.sh").exists(), "mc-init.sh not found"
    assert (driver_path / "update-aider-config.sh").exists(), "update-aider-config.sh not found"


@requires_docker
def test_aider_docker_image_build():
    """Test that the aider Docker image can be built."""
    if SKIP_DOCKER_TESTS:
        pytest.skip("Docker tests are disabled")
    
    config_manager = ConfigManager()
    driver_path = config_manager.get_driver_path("aider")
    
    # Build the Docker image
    image_tag = f"aider-test-{uuid.uuid4().hex[:8]}"
    build_cmd = ["docker", "build", "-t", image_tag, str(driver_path)]
    
    result = subprocess.run(
        build_cmd,
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0, f"Docker build failed: {result.stderr}"
    
    # Clean up the image after testing
    subprocess.run(["docker", "rmi", image_tag], capture_output=True)


@patch("docker.from_env")
@patch("mcontainer.container.docker")
@patch("mcontainer.mcp.docker")
def test_cli_create_aider_session(mock_mcp_docker, mock_container_docker, mock_docker, cli_runner, mock_container_manager):
    """Test creating an aider session via the CLI."""
    from mcontainer.cli import app
    
    # Mock docker client to avoid Docker dependency
    mock_client = MagicMock()
    mock_container_docker.from_env.return_value = mock_client
    mock_mcp_docker.from_env.return_value = mock_client
    mock_docker.return_value = mock_client
    
    # Test creating an aider session with CLI
    result = cli_runner.invoke(app, [
        "session", "create",
        "--driver", "aider",
        "--name", "test-aider-session",
        "--env", "OPENAI_API_KEY=test-key"
    ])
    
    assert result.exit_code == 0, f"CLI command failed: {result.stdout}"
    
    # Verify the session creation was called with the right driver
    mock_container_manager.create_session.assert_called_once()
    assert mock_container_manager.create_session.call_args[1]["driver_name"] == "aider"


@patch("docker.from_env")
def test_aider_modify_code(mock_docker, tmp_path):
    """Test aider's ability to modify code in a git repository."""
    if SKIP_DOCKER_TESTS:
        pytest.skip("Docker tests are disabled")
    
    # This is an integration test that will:
    # 1. Create a temporary git repository with a simple Python file
    # 2. Start an aider session with that repository mounted
    # 3. Ask aider to modify the file
    # 4. Check that the file was modified as expected
    
    # Create a simple Python file in a git repo
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repository
    subprocess.run(["git", "init", str(repo_dir)], capture_output=True, check=True)
    
    # Configure git (required for aider)
    subprocess.run(
        ["git", "config", "--local", "user.email", "test@example.com"],
        cwd=str(repo_dir),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--local", "user.name", "Test User"],
        cwd=str(repo_dir),
        capture_output=True,
    )
    
    # Create a simple Python file
    hello_py = repo_dir / "hello.py"
    hello_py.write_text('print("hello")')
    
    # Add and commit the file
    subprocess.run(["git", "add", "hello.py"], cwd=str(repo_dir), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(repo_dir),
        capture_output=True,
    )
    
    # Skip this test for now because it requires interaction with OpenAI API
    # We'll enable it later when we have proper mocks or integration tests set up
    pytest.skip("Skipping this test as it requires interactive aider session")