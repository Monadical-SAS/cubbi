"""Integration tests for cubbi images with different model combinations."""

import subprocess
import pytest
from typing import Dict


# Test matrix: all images and models to test
IMAGES = ["goose", "aider", "claudecode", "opencode", "crush"]

MODELS = [
    "anthropic/claude-sonnet-4-20250514",
    "openai/gpt-4o",
    "openrouter/openai/gpt-4o",
    "litellm/gpt-oss:120b",
]

# Command templates for each tool (based on research)
COMMANDS: Dict[str, str] = {
    "goose": "goose run -t '{prompt}' --no-session --quiet",
    "aider": "aider --message '{prompt}' --yes-always --no-fancy-input --no-check-update --no-auto-commits",
    "claudecode": "claude -p '{prompt}'",
    "opencode": "opencode run -m {model} '{prompt}'",
    "crush": "crush run '{prompt}'",
}


def run_cubbi_command(
    image: str, model: str, command: str, timeout: int = 180
) -> subprocess.CompletedProcess:
    """Run a cubbi command with specified image, model, and command."""
    full_command = [
        "uv",
        "run",
        "-m",
        "cubbi.cli",
        "session",
        "create",
        "-i",
        image,
        "-m",
        model,
        "--no-connect",
        "--no-shell",
        "--run",
        command,
    ]

    return subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd="/home/tito/code/monadical/cubbi",
    )


def is_successful_response(result: subprocess.CompletedProcess) -> bool:
    """Check if the cubbi command completed successfully."""
    # Check for successful completion markers
    return (
        result.returncode == 0
        and "Initial command finished (exit code: 0)" in result.stdout
        and "Command execution complete" in result.stdout
    )


@pytest.mark.integration
@pytest.mark.parametrize("image", IMAGES)
@pytest.mark.parametrize("model", MODELS)
def test_image_model_combination(image: str, model: str):
    """Test each image with each model using appropriate command syntax."""
    prompt = "What is 2+2?"

    # Get the command template for this image
    command_template = COMMANDS[image]

    # For opencode, we need to substitute the model in the command
    if image == "opencode":
        command = command_template.format(prompt=prompt, model=model)
    else:
        command = command_template.format(prompt=prompt)

    # Run the test
    result = run_cubbi_command(image, model, command)

    # Check if the command was successful
    assert is_successful_response(result), (
        f"Failed to run {image} with {model}. "
        f"Return code: {result.returncode}\n"
        f"Stdout: {result.stdout}\n"
        f"Stderr: {result.stderr}"
    )

    # Additional checks for specific outputs (optional)
    if image == "goose":
        # Goose should show some calculation result
        assert any(
            char.isdigit() for char in result.stdout
        ), f"Goose should provide numeric answer for math question. Output: {result.stdout}"


@pytest.mark.integration
def test_all_images_available():
    """Test that all required images are available for testing."""
    # Run image list command
    result = subprocess.run(
        ["uv", "run", "-m", "cubbi.cli", "image", "list"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/home/tito/code/monadical/cubbi",
    )

    assert result.returncode == 0, f"Failed to list images: {result.stderr}"

    # Check that all required images are listed
    for image in IMAGES:
        assert image in result.stdout, f"Image {image} not found in available images"


@pytest.mark.integration
@pytest.mark.parametrize("image", IMAGES)
def test_image_help_command(image: str):
    """Test that each image can run basic help commands."""
    help_commands = {
        "goose": "goose --help",
        "aider": "aider --help",
        "claudecode": "claude --help",
        "opencode": "opencode --help",
        "crush": "crush --help",
    }

    command = help_commands[image]
    result = run_cubbi_command(image, MODELS[0], command, timeout=60)  # Use first model

    assert is_successful_response(result), (
        f"Failed to run help command for {image}. "
        f"Return code: {result.returncode}\n"
        f"Stderr: {result.stderr}"
    )


if __name__ == "__main__":
    # Allow running the test file directly for development
    pytest.main([__file__, "-v", "-m", "integration"])
