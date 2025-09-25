"""
Interactive configuration tool for Cubbi providers and models.
"""

import os
from typing import Optional

import docker
import questionary
from rich.console import Console

from .user_config import UserConfigManager

console = Console()


class ProviderConfigurator:
    """Interactive configuration for LLM providers."""

    def __init__(self, user_config: UserConfigManager):
        self.user_config = user_config
        # Initialize Docker client for network autocomplete
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()  # Test connection
        except Exception:
            self.docker_client = None

    def run(self) -> None:
        """Run the interactive configuration tool."""
        console.print("\nCubbi Configuration\n")

        while True:
            # Get current default model for display
            current_default = self.user_config.get("defaults.model", "Not set")

            choice = questionary.select(
                "What would you like to configure?",
                choices=[
                    "Configure providers",
                    f"Set default model ({current_default})",
                    "Configure MCP servers",
                    "Configure networks",
                    "Configure volumes",
                    "Configure ports",
                    "View current configuration",
                    "Exit",
                ],
            ).ask()

            if choice == "Configure providers":
                self._configure_providers()
            elif choice and choice.startswith("Set default model"):
                self._set_default_model()
            elif choice == "Configure MCP servers":
                self._configure_mcps()
            elif choice == "Configure networks":
                self._configure_networks()
            elif choice == "Configure volumes":
                self._configure_volumes()
            elif choice == "Configure ports":
                self._configure_ports()
            elif choice == "View current configuration":
                self._show_current_config()
            elif choice == "Exit" or choice is None:
                console.print("\n[green]Configuration complete![/green]")
                break

    def _configure_providers(self) -> None:
        """Configure LLM providers."""
        while True:
            providers = self.user_config.list_providers()

            choices = []

            # Add existing providers
            for name, config in providers.items():
                provider_type = config.get("type", "unknown")
                base_url = config.get("base_url")
                if base_url:
                    choices.append(f"{name} ({provider_type}) - {base_url}")
                else:
                    choices.append(f"{name} ({provider_type})")

            # Add separator and options
            if choices:
                choices.append("---")
            choices.extend(["Add new provider", "Back to main menu"])

            choice = questionary.select(
                "Select a provider to configure:",
                choices=choices,
            ).ask()

            if choice is None or choice == "Back to main menu":
                break
            elif choice == "Add new provider":
                self._add_new_provider()
            else:
                # Extract provider name from the choice
                # Format: "provider_name (provider_type)" or "provider_name (provider_type) - base_url"
                provider_name = choice.split(" (")[0]
                self._edit_provider(provider_name)

    def _add_new_provider(self) -> None:
        """Add a new provider configuration."""
        OTHER = "Other (openai compatible)"
        # Ask for provider type
        provider_type = questionary.select(
            "Select provider type:",
            choices=[
                "Anthropic",
                "OpenAI",
                "Google",
                "OpenRouter",
                OTHER,
            ],
        ).ask()

        if provider_type is None:
            return

        # Map display names to internal types
        type_mapping = {
            "Anthropic": "anthropic",
            "OpenAI": "openai",
            "Google": "google",
            "OpenRouter": "openrouter",
            OTHER: "openai",
        }

        internal_type = type_mapping[provider_type]

        # Ask for provider name
        if provider_type == OTHER:
            provider_name = questionary.text(
                "Enter a name for this provider (e.g., 'litellm', 'local-llm'):",
                validate=lambda name: len(name.strip()) > 0
                or "Please enter a provider name",
            ).ask()
        else:
            # Use standard name but allow customization
            standard_name = internal_type
            provider_name = questionary.text(
                "Provider name:",
                default=standard_name,
                validate=lambda name: len(name.strip()) > 0
                or "Please enter a provider name",
            ).ask()

        if provider_name is None:
            return

        provider_name = provider_name.strip()

        # Check if provider already exists
        if self.user_config.get_provider(provider_name):
            console.print(
                f"[yellow]Provider '{provider_name}' already exists![/yellow]"
            )
            return

        # Ask for API key configuration
        api_key_choice = questionary.select(
            "How would you like to provide the API key?",
            choices=[
                "Enter API key directly (saved in config)",
                "Use environment variable (recommended)",
                "No API key needed",
            ],
        ).ask()

        if api_key_choice is None:
            return

        if "environment variable" in api_key_choice:
            env_var = questionary.text(
                "Environment variable name:",
                default=f"{provider_name.upper().replace('-', '_')}_API_KEY",
                validate=lambda var: len(var.strip()) > 0
                or "Please enter a variable name",
            ).ask()

            if env_var is None:
                return

            api_key = f"${{{env_var.strip()}}}"

            if not os.environ.get(env_var.strip()):
                console.print(
                    f"[yellow]Warning: Environment variable '{env_var}' is not currently set[/yellow]"
                )
        elif "No API key" in api_key_choice:
            api_key = ""
        else:
            api_key = questionary.password(
                "Enter API key:",
                validate=lambda key: len(key.strip()) > 0 or "Please enter an API key",
            ).ask()

            if api_key is None:
                return

        base_url = None
        if internal_type == "openai" and provider_type == OTHER:
            base_url = questionary.text(
                "Base URL for API calls:",
                validate=lambda url: url.startswith("http")
                or "Please enter a valid URL starting with http",
            ).ask()

            if base_url is None:
                return

        # Add the provider
        self.user_config.add_provider(
            name=provider_name,
            provider_type=internal_type,
            api_key=api_key,
            base_url=base_url,
        )

        console.print(f"[green]Added provider '{provider_name}'[/green]")

        if self.user_config.supports_model_fetching(provider_name):
            console.print("Refreshing models...")
            try:
                self._refresh_provider_models(provider_name)
            except Exception as e:
                console.print(f"[yellow]Could not refresh models: {e}[/yellow]")

    def _edit_provider(self, provider_name: str) -> None:
        """Edit an existing provider."""
        provider_config = self.user_config.get_provider(provider_name)
        if not provider_config:
            console.print(f"[red]Provider '{provider_name}' not found![/red]")
            return

        console.print(f"\n[bold]Configuration for '{provider_name}':[/bold]")
        for key, value in provider_config.items():
            if key == "api_key" and not value.startswith("${"):
                display_value = (
                    f"{'*' * (len(value) - 4)}{value[-4:]}"
                    if len(value) > 4
                    else "****"
                )
            elif key == "models" and isinstance(value, list):
                if value:
                    console.print(f"  {key}:")
                    for i, model in enumerate(value[:10]):
                        if isinstance(model, dict):
                            model_id = model.get("id", str(model))
                        else:
                            model_id = str(model)
                        console.print(f"    {i + 1}. {model_id}")
                    if len(value) > 10:
                        console.print(
                            f"    ... and {len(value) - 10} more ({len(value)} total)"
                        )
                    continue
                else:
                    display_value = "(no models configured)"
            else:
                display_value = value
            console.print(f"  {key}: {display_value}")
        console.print()

        while True:
            choices = ["Remove provider"]

            if self.user_config.supports_model_fetching(provider_name):
                choices.append("Refresh models")

            choices.extend(["---", "Back"])

            choice = questionary.select(
                f"What would you like to do with '{provider_name}'?",
                choices=choices,
            ).ask()

            if choice == "Remove provider":
                confirm = questionary.confirm(
                    f"Are you sure you want to remove provider '{provider_name}'?",
                    default=False,
                ).ask()

                if confirm:
                    self.user_config.remove_provider(provider_name)
                    console.print(f"[green]Removed provider '{provider_name}'[/green]")
                    break

            elif choice == "Refresh models":
                self._refresh_provider_models(provider_name)

            elif choice == "Back" or choice is None:
                break

    def _refresh_provider_models(self, provider_name: str) -> None:
        from .model_fetcher import fetch_provider_models

        try:
            provider_config = self.user_config.get_provider(provider_name)
            console.print(f"Refreshing models for {provider_name}...")

            models = fetch_provider_models(provider_config)
            self.user_config.set_provider_models(provider_name, models)

            console.print(
                f"[green]Successfully refreshed {len(models)} models for '{provider_name}'[/green]"
            )

        except Exception as e:
            console.print(f"[red]Failed to refresh models: {e}[/red]")

    def _select_model_from_list(self, provider_name: str) -> Optional[str]:
        from .model_fetcher import fetch_provider_models

        models = self.user_config.list_provider_models(provider_name)

        if not models:
            console.print(f"No models found for {provider_name}. Refreshing...")
            try:
                provider_config = self.user_config.get_provider(provider_name)
                models = fetch_provider_models(provider_config)
                self.user_config.set_provider_models(provider_name, models)
                console.print(f"[green]Refreshed {len(models)} models[/green]")
            except Exception as e:
                console.print(f"[red]Failed to refresh models: {e}[/red]")
                return questionary.text(
                    f"Enter model name for {provider_name}:",
                    validate=lambda name: len(name.strip()) > 0
                    or "Please enter a model name",
                ).ask()

        if not models:
            console.print(f"[yellow]No models available for {provider_name}[/yellow]")
            return questionary.text(
                f"Enter model name for {provider_name}:",
                validate=lambda name: len(name.strip()) > 0
                or "Please enter a model name",
            ).ask()

        model_choices = [model["id"] for model in models]
        model_choices.append("---")
        model_choices.append("Enter manually")

        choice = questionary.select(
            f"Select a model for {provider_name}:",
            choices=model_choices,
        ).ask()

        if choice is None or choice == "---":
            return None
        elif choice == "Enter manually":
            return questionary.text(
                f"Enter model name for {provider_name}:",
                validate=lambda name: len(name.strip()) > 0
                or "Please enter a model name",
            ).ask()
        else:
            return choice

    def _set_default_model(self) -> None:
        """Set the default model."""
        providers = self.user_config.list_providers()

        if not providers:
            console.print(
                "[yellow]No providers configured. Please add providers first.[/yellow]"
            )
            return

        # Create choices in provider/model format
        choices = []
        for provider_name, provider_config in providers.items():
            provider_type = provider_config.get("type", "unknown")
            has_key = bool(provider_config.get("api_key"))

            # Include provider if it has an API key OR supports model fetching (might not need key)
            if has_key or self.user_config.supports_model_fetching(provider_name):
                base_url = provider_config.get("base_url")
                if base_url:
                    choices.append(f"{provider_name} ({provider_type}) - {base_url}")
                else:
                    choices.append(f"{provider_name} ({provider_type})")

        if not choices:
            console.print("[yellow]No usable providers configured.[/yellow]")
            return

        # Add separator and cancel option
        choices.append("---")
        choices.append("Back to main menu")

        choice = questionary.select(
            "Select a provider for the default model:",
            choices=choices,
        ).ask()

        if choice is None or choice == "Back to main menu" or choice == "---":
            return

        # Extract provider name
        provider_name = choice.split(" (")[0]

        if self.user_config.supports_model_fetching(provider_name):
            model_name = self._select_model_from_list(provider_name)
        else:
            model_name = questionary.text(
                f"Enter model name for {provider_name} (e.g., 'claude-3-5-sonnet', 'gpt-4', 'llama3:70b'):",
                validate=lambda name: len(name.strip()) > 0
                or "Please enter a model name",
            ).ask()

        if model_name is None:
            return

        default_model = f"{provider_name}/{model_name.strip()}"
        self.user_config.set("defaults.model", default_model)

        console.print(f"[green]Set default model to '{default_model}'[/green]")

    def _show_current_config(self) -> None:
        """Show current configuration."""
        console.print()

        # Show default model
        default_model = self.user_config.get("defaults.model", "Not set")
        console.print(f"Default model: [cyan]{default_model}[/cyan]")

        # Show providers
        console.print("\n[bold]Providers[/bold]")
        providers = self.user_config.list_providers()
        if providers:
            for name, config in providers.items():
                base_url = config.get("base_url")
                if base_url:
                    console.print(f"  - {name} ({base_url})")
                else:
                    console.print(f"  - {name}")
        else:
            console.print("  (no providers configured)")

        # Show MCP servers
        console.print("\n[bold]MCP Servers[/bold]")
        mcp_configs = self.user_config.list_mcp_configurations()
        default_mcps = self.user_config.list_mcps()
        if mcp_configs:
            for mcp_config in mcp_configs:
                name = mcp_config.get("name", "unknown")
                mcp_type = mcp_config.get("type", "unknown")
                is_default = " (default)" if name in default_mcps else ""

                # Add additional info for local MCPs
                if mcp_type == "local":
                    command = mcp_config.get("command", "")
                    args = mcp_config.get("args", [])
                    if args:
                        cmd_display = f"{command} {' '.join(args[:2])}"
                        if len(args) > 2:
                            cmd_display += "..."
                    else:
                        cmd_display = command
                    console.print(f"  - {name} ({mcp_type}: {cmd_display}){is_default}")
                else:
                    console.print(f"  - {name} ({mcp_type}){is_default}")
        else:
            console.print("  (no MCP servers configured)")

        # Show networks
        console.print("\n[bold]Networks[/bold]")
        networks = self.user_config.list_networks()
        if networks:
            for network in networks:
                console.print(f"  - {network}")
        else:
            console.print("  (no networks configured)")

        # Show volumes
        console.print("\n[bold]Volumes[/bold]")
        volumes = self.user_config.list_volumes()
        if volumes:
            for volume in volumes:
                console.print(f"  - {volume}")
        else:
            console.print("  (no volumes configured)")

        # Show ports
        console.print("\n[bold]Ports[/bold]")
        ports = self.user_config.list_ports()
        if ports:
            for port in sorted(ports):
                console.print(f"  - {port}")
        else:
            console.print("  (no ports configured)")

        console.print()

    def _get_docker_networks(self):
        """Get list of existing Docker networks for autocomplete."""
        if not self.docker_client:
            return []

        try:
            networks = self.docker_client.networks.list()
            return [network.name for network in networks if network.name != "none"]
        except Exception:
            return []

    def _configure_mcps(self) -> None:
        """Configure MCP servers."""
        while True:
            mcp_configs = self.user_config.list_mcp_configurations()
            default_mcps = self.user_config.list_mcps()

            choices = []
            if mcp_configs:
                for mcp_config in mcp_configs:
                    name = mcp_config.get("name", "unknown")
                    mcp_type = mcp_config.get("type", "unknown")
                    is_default = " ⭐" if name in default_mcps else ""
                    choices.append(f"{name} ({mcp_type}){is_default}")
                choices.append("---")

            choices.extend(["Add MCP server", "---", "Back to main menu"])

            choice = questionary.select(
                "Select an MCP server to configure:",
                choices=choices,
            ).ask()

            if choice is None or choice == "Back to main menu" or choice == "---":
                break
            elif choice == "Add MCP server":
                self._add_mcp_server()
            else:
                # Extract MCP name from choice (format: "name (type)⭐")
                mcp_name = choice.split(" (")[0]
                self._edit_mcp_server(mcp_name)

    def _add_mcp_server(self) -> None:
        """Add a new MCP server."""
        # Ask for MCP type first
        mcp_type = questionary.select(
            "Select MCP server type:",
            choices=[
                "Local MCP (stdio-based command)",
                "Remote MCP (URL-based)",
                "Docker MCP (containerized)",
                "Proxy MCP (proxy + base image)",
            ],
        ).ask()

        if mcp_type is None:
            return

        if "Local MCP" in mcp_type:
            self._add_local_mcp()
        elif "Remote MCP" in mcp_type:
            self._add_remote_mcp()
        elif "Docker MCP" in mcp_type:
            self._add_docker_mcp()
        elif "Proxy MCP" in mcp_type:
            self._add_proxy_mcp()

    def _add_remote_mcp(self) -> None:
        """Add a remote MCP server."""
        name = questionary.text(
            "Enter MCP server name:",
            validate=lambda n: len(n.strip()) > 0 or "Please enter a name",
        ).ask()

        if name is None:
            return

        url = questionary.text(
            "Enter server URL:",
            validate=lambda u: u.startswith("http")
            or "Please enter a valid URL starting with http",
        ).ask()

        if url is None:
            return

        # Ask for optional headers
        add_headers = questionary.confirm("Add custom headers?").ask()
        headers = {}

        if add_headers:
            while True:
                header_name = questionary.text("Header name (empty to finish):").ask()
                if not header_name or not header_name.strip():
                    break

                header_value = questionary.text(f"Value for {header_name}:").ask()
                if header_value:
                    headers[header_name.strip()] = header_value.strip()

        mcp_config = {
            "name": name.strip(),
            "type": "remote",
            "url": url.strip(),
            "headers": headers,
        }

        self.user_config.add_mcp_configuration(mcp_config)

        # Ask if it should be a default
        make_default = questionary.confirm(f"Add '{name}' to default MCPs?").ask()
        if make_default:
            self.user_config.add_mcp(name.strip())

        console.print(f"[green]Added remote MCP server '{name}'[/green]")

    def _add_docker_mcp(self) -> None:
        """Add a Docker MCP server."""
        name = questionary.text(
            "Enter MCP server name:",
            validate=lambda n: len(n.strip()) > 0 or "Please enter a name",
        ).ask()

        if name is None:
            return

        image = questionary.text(
            "Enter Docker image:",
            validate=lambda i: len(i.strip()) > 0 or "Please enter an image",
        ).ask()

        if image is None:
            return

        command = questionary.text(
            "Enter command to run (optional):",
        ).ask()

        # Ask for environment variables
        add_env = questionary.confirm("Add environment variables?").ask()
        env = {}

        if add_env:
            while True:
                env_name = questionary.text(
                    "Environment variable name (empty to finish):"
                ).ask()
                if not env_name or not env_name.strip():
                    break

                env_value = questionary.text(f"Value for {env_name}:").ask()
                if env_value:
                    env[env_name.strip()] = env_value.strip()

        mcp_config = {
            "name": name.strip(),
            "type": "docker",
            "image": image.strip(),
            "command": command.strip() if command else "",
            "env": env,
        }

        self.user_config.add_mcp_configuration(mcp_config)

        # Ask if it should be a default
        make_default = questionary.confirm(f"Add '{name}' to default MCPs?").ask()
        if make_default:
            self.user_config.add_mcp(name.strip())

        console.print(f"[green]Added Docker MCP server '{name}'[/green]")

    def _add_proxy_mcp(self) -> None:
        """Add a Proxy MCP server."""
        name = questionary.text(
            "Enter MCP server name:",
            validate=lambda n: len(n.strip()) > 0 or "Please enter a name",
        ).ask()

        if name is None:
            return

        base_image = questionary.text(
            "Enter base Docker image (the actual MCP server):",
            validate=lambda i: len(i.strip()) > 0 or "Please enter a base image",
        ).ask()

        if base_image is None:
            return

        proxy_image = questionary.text(
            "Enter proxy Docker image:",
            default="mcp-proxy",
        ).ask()

        if proxy_image is None:
            return

        command = questionary.text(
            "Enter command to run in base image (optional):",
        ).ask()

        host_port = questionary.text(
            "Enter host port (optional, will auto-assign if empty):",
            validate=lambda p: not p.strip()
            or (p.strip().isdigit() and 1 <= int(p.strip()) <= 65535)
            or "Please enter a valid port number (1-65535) or leave empty",
        ).ask()

        # Ask for environment variables
        add_env = questionary.confirm("Add environment variables?").ask()
        env = {}

        if add_env:
            while True:
                env_name = questionary.text(
                    "Environment variable name (empty to finish):"
                ).ask()
                if not env_name or not env_name.strip():
                    break

                env_value = questionary.text(f"Value for {env_name}:").ask()
                if env_value:
                    env[env_name.strip()] = env_value.strip()

        mcp_config = {
            "name": name.strip(),
            "type": "proxy",
            "base_image": base_image.strip(),
            "proxy_image": proxy_image.strip(),
            "command": command.strip() if command else "",
            "proxy_options": {
                "sse_port": 8080,
                "sse_host": "0.0.0.0",
                "allow_origin": "*",
            },
            "env": env,
        }

        if host_port and host_port.strip():
            mcp_config["host_port"] = int(host_port.strip())

        self.user_config.add_mcp_configuration(mcp_config)

        # Ask if it should be a default
        make_default = questionary.confirm(f"Add '{name}' to default MCPs?").ask()
        if make_default:
            self.user_config.add_mcp(name.strip())

        console.print(f"[green]Added Proxy MCP server '{name}'[/green]")

    def _add_local_mcp(self) -> None:
        """Add a local MCP server."""
        name = questionary.text(
            "Enter MCP server name:",
            validate=lambda n: len(n.strip()) > 0 or "Please enter a name",
        ).ask()

        if name is None:
            return

        command = questionary.text(
            "Enter command path (e.g., 'npx', '/usr/bin/node', 'python'):",
            validate=lambda c: len(c.strip()) > 0 or "Please enter a command",
        ).ask()

        if command is None:
            return

        # Ask for command arguments
        args = []
        add_args = questionary.confirm("Add command arguments?").ask()

        if add_args:
            console.print(
                "[dim]Enter arguments one per line (empty line to finish):[/dim]"
            )
            while True:
                arg = questionary.text("Argument:").ask()
                if not arg or not arg.strip():
                    break
                args.append(arg.strip())

        # Ask for environment variables
        add_env = questionary.confirm("Add environment variables?").ask()
        env = {}

        if add_env:
            while True:
                env_name = questionary.text(
                    "Environment variable name (empty to finish):"
                ).ask()
                if not env_name or not env_name.strip():
                    break

                env_value = questionary.text(f"Value for {env_name}:").ask()
                if env_value:
                    env[env_name.strip()] = env_value.strip()

        mcp_config = {
            "name": name.strip(),
            "type": "local",
            "command": command.strip(),
            "args": args,
            "env": env,
        }

        self.user_config.add_mcp_configuration(mcp_config)

        # Ask if it should be a default
        make_default = questionary.confirm(f"Add '{name}' to default MCPs?").ask()
        if make_default:
            self.user_config.add_mcp(name.strip())

        console.print(f"[green]Added local MCP server '{name}'[/green]")
        if args:
            console.print(f"  Command: {command} {' '.join(args)}")
        else:
            console.print(f"  Command: {command}")

    def _edit_mcp_server(self, server_name: str) -> None:
        """Edit an existing MCP server."""
        mcp_config = self.user_config.get_mcp_configuration(server_name)
        if not mcp_config:
            console.print(f"[red]MCP server '{server_name}' not found![/red]")
            return

        is_default = server_name in self.user_config.list_mcps()

        choices = [
            "View configuration",
            f"{'Remove from' if is_default else 'Add to'} defaults",
            "Remove server",
            "---",
            "Back",
        ]

        choice = questionary.select(
            f"What would you like to do with MCP server '{server_name}'?",
            choices=choices,
        ).ask()

        if choice == "View configuration":
            console.print("\n[bold]MCP server configuration:[/bold]")
            for key, value in mcp_config.items():
                if key == "args" and isinstance(value, list) and value:
                    console.print(f"  {key}:")
                    for arg in value:
                        console.print(f"    - {arg}")
                elif isinstance(value, dict) and value:
                    console.print(f"  {key}:")
                    for sub_key, sub_value in value.items():
                        console.print(f"    {sub_key}: {sub_value}")
                elif isinstance(value, list) and value:
                    console.print(f"  {key}: {', '.join(map(str, value))}")
                else:
                    console.print(f"  {key}: {value}")
            console.print()

        elif "defaults" in choice:
            if is_default:
                confirm = questionary.confirm(
                    f"Remove '{server_name}' from default MCPs?", default=False
                ).ask()
                if confirm:
                    self.user_config.remove_mcp(server_name)
                    console.print(
                        f"[green]Removed '{server_name}' from default MCPs[/green]"
                    )
            else:
                self.user_config.add_mcp(server_name)
                console.print(f"[green]Added '{server_name}' to default MCPs[/green]")

        elif choice == "Remove server":
            confirm = questionary.confirm(
                f"Are you sure you want to remove MCP server '{server_name}'?",
                default=False,
            ).ask()

            if confirm:
                if self.user_config.remove_mcp_configuration(server_name):
                    console.print(f"[green]Removed MCP server '{server_name}'[/green]")
                else:
                    console.print(
                        f"[red]Failed to remove MCP server '{server_name}'[/red]"
                    )

    def _configure_networks(self) -> None:
        """Configure default networks."""
        while True:
            networks = self.user_config.list_networks()

            choices = []
            if networks:
                for network in networks:
                    choices.append(f"{network}")
                choices.append("---")

            choices.extend(["Add network", "---", "Back to main menu"])

            choice = questionary.select(
                "Select a network to configure:",
                choices=choices,
            ).ask()

            if choice is None or choice == "Back to main menu" or choice == "---":
                break
            elif choice == "Add network":
                self._add_network()
            else:
                # Edit network
                self._edit_network(choice)

    def _add_network(self) -> None:
        """Add a new network."""
        # Get existing Docker networks for autocomplete
        docker_networks = self._get_docker_networks()

        if docker_networks:
            network_name = questionary.autocomplete(
                "Enter Docker network name:",
                choices=docker_networks,
                validate=lambda name: len(name.strip()) > 0
                or "Please enter a network name",
            ).ask()
        else:
            # Fallback to text input if Docker is not available
            network_name = questionary.text(
                "Enter Docker network name:",
                validate=lambda name: len(name.strip()) > 0
                or "Please enter a network name",
            ).ask()

        if network_name is None:
            return

        network_name = network_name.strip()
        self.user_config.add_network(network_name)
        console.print(f"[green]Added network '{network_name}'[/green]")

    def _edit_network(self, network_name: str) -> None:
        """Edit an existing network."""
        choices = ["View configuration", "Remove network", "---", "Back"]

        choice = questionary.select(
            f"What would you like to do with network '{network_name}'?",
            choices=choices,
        ).ask()

        if choice == "View configuration":
            console.print("\n[bold]Network configuration:[/bold]")
            console.print(f"  Name: {network_name}")
            console.print()

        elif choice == "Remove network":
            confirm = questionary.confirm(
                f"Are you sure you want to remove network '{network_name}'?",
                default=False,
            ).ask()

            if confirm:
                self.user_config.remove_network(network_name)
                console.print(f"[green]Removed network '{network_name}'[/green]")

    def _configure_volumes(self) -> None:
        """Configure default volume mappings."""
        while True:
            volumes = self.user_config.list_volumes()

            choices = []
            if volumes:
                for volume in volumes:
                    choices.append(f"{volume}")
                choices.append("---")

            choices.extend(["Add volume mapping", "---", "Back to main menu"])

            choice = questionary.select(
                "Select a volume to configure:",
                choices=choices,
            ).ask()

            if choice is None or choice == "Back to main menu" or choice == "---":
                break
            elif choice == "Add volume mapping":
                self._add_volume()
            else:
                # Edit volume
                self._edit_volume(choice)

    def _add_volume(self) -> None:
        """Add a new volume mapping."""
        # Ask for source directory
        source = questionary.path(
            "Enter source directory path:",
            validate=lambda path: len(path.strip()) > 0 or "Please enter a source path",
        ).ask()

        if source is None:
            return

        # Ask for destination directory
        destination = questionary.text(
            "Enter destination path in container:",
            validate=lambda path: len(path.strip()) > 0
            or "Please enter a destination path",
        ).ask()

        if destination is None:
            return

        # Create the volume mapping
        volume_mapping = f"{source.strip()}:{destination.strip()}"
        self.user_config.add_volume(volume_mapping)
        console.print(f"[green]Added volume mapping '{volume_mapping}'[/green]")

    def _edit_volume(self, volume_mapping: str) -> None:
        """Edit an existing volume mapping."""
        choices = ["View configuration", "Remove volume", "---", "Back"]

        choice = questionary.select(
            f"What would you like to do with volume '{volume_mapping}'?",
            choices=choices,
        ).ask()

        if choice == "View configuration":
            console.print("\n[bold]Volume mapping configuration:[/bold]")
            if ":" in volume_mapping:
                source, destination = volume_mapping.split(":", 1)
                console.print(f"  Source: {source}")
                console.print(f"  Destination: {destination}")
            else:
                console.print(f"  Mapping: {volume_mapping}")
            console.print()

        elif choice == "Remove volume":
            confirm = questionary.confirm(
                f"Are you sure you want to remove volume mapping '{volume_mapping}'?",
                default=False,
            ).ask()

            if confirm:
                self.user_config.remove_volume(volume_mapping)
                console.print(
                    f"[green]Removed volume mapping '{volume_mapping}'[/green]"
                )

    def _configure_ports(self) -> None:
        """Configure default port forwards."""
        while True:
            ports = self.user_config.list_ports()

            choices = []
            if ports:
                for port in sorted(ports):
                    choices.append(f"{port}")
                choices.append("---")

            choices.extend(["Add port", "---", "Back to main menu"])

            choice = questionary.select(
                "Select a port to configure:",
                choices=choices,
            ).ask()

            if choice is None or choice == "Back to main menu" or choice == "---":
                break
            elif choice == "Add port":
                self._add_port()
            else:
                # Edit port
                try:
                    port_num = int(choice)
                    self._edit_port(port_num)
                except ValueError:
                    pass

    def _add_port(self) -> None:
        """Add a new port forward."""

        def validate_port(value: str) -> bool:
            try:
                port = int(value.strip())
                return 1 <= port <= 65535
            except ValueError:
                return False

        port_str = questionary.text(
            "Enter port number (1-65535):",
            validate=lambda p: validate_port(p)
            or "Please enter a valid port number (1-65535)",
        ).ask()

        if port_str is None:
            return

        port_num = int(port_str.strip())
        self.user_config.add_port(port_num)
        console.print(f"[green]Added port {port_num}[/green]")

    def _edit_port(self, port_num: int) -> None:
        """Edit an existing port forward."""
        choices = ["Remove port", "---", "Back"]

        choice = questionary.select(
            f"What would you like to do with port {port_num}?",
            choices=choices,
        ).ask()

        if choice == "Remove port":
            confirm = questionary.confirm(
                f"Are you sure you want to remove port {port_num}?", default=False
            ).ask()

            if confirm:
                self.user_config.remove_port(port_num)
                console.print(f"[green]Removed port {port_num}[/green]")


def run_interactive_config() -> None:
    """Entry point for the interactive configuration tool."""
    user_config = UserConfigManager()
    configurator = ProviderConfigurator(user_config)
    configurator.run()


if __name__ == "__main__":
    run_interactive_config()
