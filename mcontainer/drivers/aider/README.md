# Aider Driver for Monadical Container

This driver provides a containerized environment for running [aider](https://aider.chat), an AI pair programming tool that integrates directly with your codebase through Git.

## Features

- Full aider environment with OpenAI API integration
- Git integration for code repositories
- Persistent configuration and chat history
- SSH server for remote access
- Support for various editors (vim, nano, etc.)

## Environment Variables

The aider driver supports the following environment variables:

- `OPENAI_API_KEY`: (Required) Your OpenAI API key
- `OPENAI_API_BASE`: (Optional) Custom OpenAI API base URL (for Azure, etc.)
- `OPENAI_MODEL`: (Optional) OpenAI model to use (default is gpt-4)
- `AIDER_EDITOR`: (Optional) Editor to use (vim, nano, emacs, code)
- `MC_PROJECT_URL`: (Optional) Git repository URL to clone
- `MC_GIT_SSH_KEY`: (Optional) SSH key for Git authentication
- `MC_GIT_TOKEN`: (Optional) Token for Git authentication

## Usage

### Creating a New Session

```bash
mc session create --driver aider --env OPENAI_API_KEY=your_api_key
```

### Using with an Existing Project

```bash
mc session create --driver aider --env OPENAI_API_KEY=your_api_key --project your_project_directory
```

### Using with a Remote Git Repository

```bash
mc session create --driver aider --env OPENAI_API_KEY=your_api_key --env MC_PROJECT_URL=https://github.com/username/repo
```

## Using Aider

Once the session is created, you'll get a shell. Inside the container, you can:

1. Navigate to your code directory
2. Run `aider` to start the AI assistant
3. Type instructions or questions to modify your code

Example:

```
$ aider src/
Welcome to aider! I'll help you edit code using AI.

I'll help you implement that. Let's start by...
```

## Persistent Configuration

Aider configuration and chat history are stored in persistent volumes:

- `/app/.aider`: Stores aider's chat history and working files
- `/root/.config/aider`: Stores aider's configuration

These directories are preserved between sessions when using the same container name.