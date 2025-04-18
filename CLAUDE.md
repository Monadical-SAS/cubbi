# Cubbi Container Development Guide

## Build Commands
```bash
# Install dependencies using uv (Astral)
uv sync

# Run Cubbi CLI
uv run -m cubbi.cli
```

## Lint/Test Commands
```bash
# Run linting
uvx ruff check .

# Run type checking (note: currently has unresolved stub dependencies)
# Skip for now during development
# uv run --with=mypy mypy .

# Run formatting
uvx ruff format .

# Run all tests
uv run -m pytest

# Run a specific test
uv run -m pytest tests/path/to/test_file.py::test_function

## Dependencies management

DO not use pip.
Use uv instead:
- Add a dep: uv add <dep>
- Remove a dep: uv remove <dep>
- Update deps: uv sync
```

## Code Style Guidelines
- **Imports**: Group standard library, third-party, and local imports with a blank line between groups
- **Formatting**: Use Ruff with 88 character line length
- **Types**: Use type annotations everywhere; import types from typing module
- **Naming**: Use snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **Error Handling**: Use specific exceptions with meaningful error messages
- **Documentation**: Use docstrings for all public functions, classes, and methods
- **Logging**: Use the structured logging module; avoid print statements
- **Async**: Use async/await for non-blocking operations, especially in FastAPI endpoints
- **Configuration**: Use environment variables with YAML for configuration

Refer to SPECIFICATIONS.md for detailed architecture and implementation guidance.
