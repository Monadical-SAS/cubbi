# Claude Container Image

This container provides a Claude Code CLI environment for AI-assisted development.

## Features

- Claude Code CLI pre-installed
- Python 3.11 with uv package manager
- Node.js 23.x with npm
- Git for version control
- SSH server (optional)
- User isolation with cubbi user

## Usage

The container is designed to work with the Cubbi container management system. Claude CLI is automatically installed and available in the user's PATH.

## Tools Included

- `claude` - Claude Code CLI
- `python` - Python 3.11
- `uv` - Fast Python package installer
- `node` - Node.js 23.x
- `npm` - Node package manager
- `git` - Version control system