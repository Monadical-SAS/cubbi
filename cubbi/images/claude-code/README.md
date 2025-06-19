# Claude Code Cubbi Image

This directory contains the Cubbi image configuration for Claude Code, an AI-powered development assistant.

## Features

- **Claude Code**: AI-powered development assistant with CLI interface
- **Development Tools**: Git, ripgrep, tmux, and standard development utilities
- **MCP Integration**: Support for Model Context Protocol servers
- **Persistent Configuration**: Maintains Claude Code settings across container restarts

## Environment Variables

### Required
- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude Code

## Persistent Configuration

The image maintains persistent configuration for:
- `~/.claude/`: Claude Code configuration directory
- `~/.claude.json`: Claude Code configuration file

## Usage

1. Build the image:
   ```bash
   docker build -t monadical/cubbi-claude-code:latest .
   ```

2. Run with Cubbi:
   ```bash
   cubbi run claude-code
   ```

## MCP Server Integration

The image automatically integrates with available MCP servers configured in the Cubbi environment, allowing Claude Code to access additional tools and capabilities.
