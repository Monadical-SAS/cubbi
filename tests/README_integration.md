# Integration Tests

This directory contains integration tests for cubbi images with different model combinations.

## Test Matrix

The integration tests cover:
- **5 Images**: goose, aider, claudecode, opencode, crush
- **4 Models**: anthropic/claude-sonnet-4-20250514, openai/gpt-4o, openrouter/openai/gpt-4o, litellm/gpt-oss:120b
- **Total**: 20 image/model combinations + additional tests

## Running Tests

### Default (Skip Integration)
```bash
# Regular tests only (integration tests excluded by default)
uv run -m pytest

# Specific test file (excluding integration)
uv run -m pytest tests/test_cli.py
```

### Integration Tests Only
```bash
# Run all integration tests (20 combinations + helpers)
uv run -m pytest -m integration

# Run specific image with all models
uv run -m pytest -m integration -k "goose"

# Run specific model with all images
uv run -m pytest -m integration -k "anthropic"

# Run single combination
uv run -m pytest -m integration -k "goose and anthropic"

# Verbose output with timing
uv run -m pytest -m integration -v -s
```

### Combined Tests
```bash
# Run both regular and integration tests
uv run -m pytest -m "not slow"  # or remove the default marker exclusion
```

## Test Structure

### `test_image_model_combination`
- Parametrized test with all image/model combinations
- Tests single prompt/response functionality
- Uses appropriate command syntax for each tool
- Verifies successful completion and basic output

### `test_image_help_command`
- Tests help command for each image
- Ensures basic functionality works

### `test_all_images_available`
- Verifies all required images are built and available

## Command Templates

Each image uses its specific command syntax:
- **goose**: `goose run -t 'prompt' --no-session --quiet`
- **aider**: `aider --message 'prompt' --yes-always --no-fancy-input --no-check-update --no-auto-commits`
- **claudecode**: `claude -p 'prompt'`
- **opencode**: `opencode run -m MODEL 'prompt'`
- **crush**: `crush run 'prompt'`

## Expected Results

All tests should pass when:
1. Images are built (`uv run -m cubbi.cli image build [IMAGE]`)
2. API keys are configured (`uv run -m cubbi.cli configure`)
3. Models are accessible and working

## Debugging Failed Tests

If tests fail, check:
1. Image availability: `uv run -m cubbi.cli image list`
2. Configuration: `uv run -m cubbi.cli config list`
3. Manual test: `uv run -m cubbi.cli session create -i IMAGE -m MODEL --run "COMMAND"`