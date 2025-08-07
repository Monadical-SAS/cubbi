"""Integration tests for cubbi images with different model combinations."""

import subprocess
import pytest
from typing import Dict


IMAGES = ["goose", "aider", "opencode", "crush"]

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
    "opencode": "opencode run '{prompt}'",
    "crush": "crush run -q '{prompt}'",
}


def run_cubbi_command(
    image: str, model: str, command: str, timeout: int = 20
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

    # Run the test with timeout handling
    try:
        result = run_cubbi_command(image, model, command)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Test timed out after 20s for {image} with {model}")

    # Check if the command was successful
    assert is_successful_response(result), (
        f"Failed to run {image} with {model}. "
        f"Return code: {result.returncode}\n"
        f"Stdout: {result.stdout}\n"
        f"Stderr: {result.stderr}"
    )


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

    for image in IMAGES:
        assert image in result.stdout, f"Image {image} not found in available images"


@pytest.mark.integration
def test_claudecode():
    """Test Claude Code without model preselection since it only supports Anthropic."""
    command = "claude -p hello"

    try:
        result = run_cubbi_command("claudecode", MODELS[0], command, timeout=20)
    except subprocess.TimeoutExpired:
        pytest.fail("Claude Code help command timed out after 20s")

    assert is_successful_response(result), (
        f"Failed to run Claude Code help command. "
        f"Return code: {result.returncode}\n"
        f"Stdout: {result.stdout}\n"
        f"Stderr: {result.stderr}"
    )


if __name__ == "__main__":
    # Allow running the test file directly for development
    pytest.main([__file__, "-v", "-m", "integration"])
