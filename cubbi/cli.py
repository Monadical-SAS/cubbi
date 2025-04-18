"""
CLI for Cubbi Container Tool.
"""

import logging
import os
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigManager
from .container import ContainerManager
from .mcp import MCPManager
from .models import SessionStatus
from .session import SessionManager
from .user_config import UserConfigManager

# Configure logging - will only show logs if --verbose flag is used
logging.basicConfig(
    level=logging.WARNING,  # Default to WARNING level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

app = typer.Typer(help="Cubbi Container Tool", no_args_is_help=True)
session_app = typer.Typer(help="Manage Cubbi sessions", no_args_is_help=True)
image_app = typer.Typer(help="Manage Cubbi images", no_args_is_help=True)
config_app = typer.Typer(help="Manage Cubbi configuration", no_args_is_help=True)
mcp_app = typer.Typer(help="Manage MCP servers", no_args_is_help=True)
app.add_typer(session_app, name="session", no_args_is_help=True)
app.add_typer(image_app, name="image", no_args_is_help=True)
app.add_typer(config_app, name="config", no_args_is_help=True)
app.add_typer(mcp_app, name="mcp", no_args_is_help=True)

console = Console()
config_manager = ConfigManager()
user_config = UserConfigManager()
session_manager = SessionManager()
container_manager = ContainerManager(config_manager, session_manager, user_config)
mcp_manager = MCPManager(config_manager=user_config)


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Cubbi Container Tool

    Run 'cubbi session create' to create a new session.
    Use 'cubbix' as a shortcut for 'cubbi session create'.
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.INFO)


@app.command()
def version() -> None:
    """Show Cubbi version information"""
    from importlib.metadata import version as get_version

    try:
        version_str = get_version("cubbi")
        console.print(f"Cubbi - Cubbi Container Tool v{version_str}")
    except Exception:
        console.print("Cubbi - Cubbi Container Tool (development version)")


@session_app.command("list")
def list_sessions() -> None:
    """List active Cubbi sessions"""
    sessions = container_manager.list_sessions()

    if not sessions:
        console.print("No active sessions found")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Image")
    table.add_column("Status")
    table.add_column("Ports")

    for session in sessions:
        ports_str = ", ".join(
            [
                f"{container_port}:{host_port}"
                for container_port, host_port in session.ports.items()
            ]
        )

        status_color = {
            SessionStatus.RUNNING: "green",
            SessionStatus.STOPPED: "red",
            SessionStatus.CREATING: "yellow",
            SessionStatus.FAILED: "red",
        }.get(session.status, "white")

        status_name = (
            session.status.value
            if hasattr(session.status, "value")
            else str(session.status)
        )

        table.add_row(
            session.id,
            session.name,
            session.image,
            f"[{status_color}]{status_name}[/{status_color}]",
            ports_str,
        )

    console.print(table)


@session_app.command("create")
def create_session(
    image: Optional[str] = typer.Option(None, "--image", "-i", help="Image to use"),
    path_or_url: Optional[str] = typer.Argument(
        None,
        help="Local directory path to mount or repository URL to clone",
        show_default=False,
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        help="Project name for configuration persistence (if not specified, no persistent configuration will be used)",
    ),
    env: List[str] = typer.Option(
        [], "--env", "-e", help="Environment variables (KEY=VALUE)"
    ),
    volume: List[str] = typer.Option(
        [], "--volume", "-v", help="Mount volumes (LOCAL_PATH:CONTAINER_PATH)"
    ),
    network: List[str] = typer.Option(
        [], "--network", "-N", help="Connect to additional Docker networks"
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Session name"),
    run_command: Optional[str] = typer.Option(
        None,
        "--run",
        help="Command to execute inside the container before starting the shell",
    ),
    no_connect: bool = typer.Option(
        False, "--no-connect", help="Don't automatically connect to the session"
    ),
    mcp: List[str] = typer.Option(
        [],
        "--mcp",
        "-m",
        help="Attach MCP servers to the session (can be specified multiple times)",
    ),
    uid: Optional[int] = typer.Option(
        None, "--uid", help="User ID to run the container as (defaults to host user)"
    ),
    gid: Optional[int] = typer.Option(
        None, "--gid", help="Group ID to run the container as (defaults to host user)"
    ),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Provider to use"
    ),
    ssh: bool = typer.Option(False, "--ssh", help="Start SSH server in the container"),
) -> None:
    """Create a new Cubbi session

    If a local directory path is provided, it will be mounted at /app in the container.
    If a repository URL is provided, it will be cloned into /app during initialization.
    If no path or URL is provided, no local volume will be mounted.

    Use --project to specify a project name for configuration persistence.
    If --project is not specified, no persistent configuration will be used.
    """
    # Determine UID/GID
    target_uid = uid if uid is not None else os.getuid()
    target_gid = gid if gid is not None else os.getgid()
    console.print(f"Using UID: {target_uid}, GID: {target_gid}")

    # Use default image from user configuration
    if not image:
        image_name = user_config.get(
            "defaults.image", config_manager.config.defaults.get("image", "goose")
        )
    else:
        image_name = image

    # Start with environment variables from user configuration
    environment = user_config.get_environment_variables()

    # Override with environment variables from command line
    for var in env:
        if "=" in var:
            key, value = var.split("=", 1)
            environment[key] = value
        else:
            console.print(
                f"[yellow]Warning: Ignoring invalid environment variable format: {var}[/yellow]"
            )

    # Parse volume mounts
    volume_mounts = {}

    # Get default volumes from user config
    default_volumes = user_config.get("defaults.volumes", [])

    # Combine default volumes with user-specified volumes
    all_volumes = default_volumes + list(volume)

    for vol in all_volumes:
        if ":" in vol:
            local_path, container_path = vol.split(":", 1)
            # Convert to absolute path if relative
            if not os.path.isabs(local_path):
                local_path = os.path.abspath(local_path)

            # Validate local path exists
            if not os.path.exists(local_path):
                console.print(
                    f"[yellow]Warning: Local path '{local_path}' does not exist. Volume will not be mounted.[/yellow]"
                )
                continue

            # Add to volume mounts (later entries override earlier ones with same host path)
            volume_mounts[local_path] = {"bind": container_path, "mode": "rw"}
        else:
            console.print(
                f"[yellow]Warning: Ignoring invalid volume format: {vol}. Use LOCAL_PATH:CONTAINER_PATH.[/yellow]"
            )

    # Get default networks from user config
    default_networks = user_config.get("defaults.networks", [])

    # Combine default networks with user-specified networks, removing duplicates
    all_networks = list(set(default_networks + network))

    # Get default MCPs from user config if none specified
    all_mcps = mcp if isinstance(mcp, list) else []
    if not all_mcps:
        default_mcps = user_config.get("defaults.mcps", [])
        all_mcps = default_mcps

        if default_mcps:
            console.print(f"Using default MCP servers: {', '.join(default_mcps)}")

    if all_networks:
        console.print(f"Networks: {', '.join(all_networks)}")

    # Show volumes that will be mounted
    if volume_mounts:
        console.print("Volumes:")
        for host_path, mount_info in volume_mounts.items():
            console.print(f"  {host_path} -> {mount_info['bind']}")

    with console.status(f"Creating session with image '{image_name}'..."):
        # If path_or_url is a local directory, we should mount it
        # If it's a Git URL or doesn't exist, handle accordingly
        mount_local = False
        if path_or_url and os.path.isdir(os.path.expanduser(path_or_url)):
            mount_local = True

        session = container_manager.create_session(
            image_name=image_name,
            project=path_or_url,
            project_name=project,
            environment=environment,
            session_name=name,
            mount_local=mount_local,
            volumes=volume_mounts,
            networks=all_networks,
            mcp=all_mcps,
            run_command=run_command,
            uid=target_uid,
            gid=target_gid,
            ssh=ssh,
            model=model,
            provider=provider,
        )

    if session:
        console.print("[green]Session created successfully![/green]")
        console.print(f"Session ID: {session.id}")
        console.print(f"Image: {session.image}")

        if session.ports:
            console.print("Ports:")
            for container_port, host_port in session.ports.items():
                console.print(f"  {container_port} -> {host_port}")

        # Auto-connect based on user config, unless overridden by --no-connect flag
        auto_connect = user_config.get("defaults.connect", True)
        # Connect if auto_connect is enabled and --no-connect wasn't used.
        # The --run command no longer prevents connection.
        should_connect = not no_connect and auto_connect
        if should_connect:
            container_manager.connect_session(session.id)
        else:
            # Explain why connection was skipped
            if no_connect:
                console.print("\nConnection skipped due to --no-connect.")
                console.print(
                    f"Connect manually with:\n  cubbi session connect {session.id}"
                )
            elif not auto_connect:
                console.print(
                    f"\nAuto-connect disabled. Connect with:\n  cubbi session connect {session.id}"
                )
    else:
        console.print("[red]Failed to create session[/red]")


@session_app.command("close")
def close_session(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to close"),
    all_sessions: bool = typer.Option(False, "--all", help="Close all active sessions"),
) -> None:
    """Close a Cubbi session or all sessions"""
    if all_sessions:
        # Get sessions first to display them
        sessions = container_manager.list_sessions()
        if not sessions:
            console.print("No active sessions to close")
            return

        console.print(f"Closing {len(sessions)} sessions...")

        # Simple progress function that prints a line when a session is closed
        def update_progress(session_id, status, message):
            if status == "completed":
                console.print(
                    f"[green]Session {session_id} closed successfully[/green]"
                )
            elif status == "failed":
                console.print(
                    f"[red]Failed to close session {session_id}: {message}[/red]"
                )

        # Start closing sessions with progress updates
        count, success = container_manager.close_all_sessions(update_progress)

        # Final result
        if success:
            console.print(f"[green]{count} sessions closed successfully[/green]")
        else:
            console.print("[red]Failed to close all sessions[/red]")
    elif session_id:
        with console.status(f"Closing session {session_id}..."):
            success = container_manager.close_session(session_id)

        if success:
            console.print(f"[green]Session {session_id} closed successfully[/green]")
        else:
            console.print(f"[red]Failed to close session {session_id}[/red]")
    else:
        console.print("[red]Error: Please provide a session ID or use --all flag[/red]")


@session_app.command("connect")
def connect_session(
    session_id: str = typer.Argument(..., help="Session ID to connect to"),
) -> None:
    """Connect to a Cubbi session"""
    console.print(f"Connecting to session {session_id}...")
    success = container_manager.connect_session(session_id)

    if not success:
        console.print(f"[red]Failed to connect to session {session_id}[/red]")


@session_app.command("logs")
def session_logs(
    session_id: str = typer.Argument(..., help="Session ID to get logs from"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    init: bool = typer.Option(
        False, "--init", "-i", help="Show initialization logs instead of container logs"
    ),
) -> None:
    """Stream logs from a Cubbi session"""
    if init:
        # Show initialization logs
        if follow:
            console.print(
                f"Streaming initialization logs from session {session_id}... (Ctrl+C to exit)"
            )
            container_manager.get_init_logs(session_id, follow=True)
        else:
            logs = container_manager.get_init_logs(session_id)
            if logs:
                console.print(logs)
    else:
        # Show regular container logs
        if follow:
            console.print(
                f"Streaming logs from session {session_id}... (Ctrl+C to exit)"
            )
            container_manager.get_session_logs(session_id, follow=True)
        else:
            logs = container_manager.get_session_logs(session_id)
            if logs:
                console.print(logs)


@image_app.command("list")
def list_images() -> None:
    """List available Cubbi images"""
    images = config_manager.list_images()

    if not images:
        console.print("No images found")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Version")
    table.add_column("Maintainer")
    table.add_column("Image")

    for name, image in images.items():
        table.add_row(
            image.name,
            image.description,
            image.version,
            image.maintainer,
            image.image,
        )

    console.print(table)


@image_app.command("build")
def build_image(
    image_name: str = typer.Argument(..., help="Image name to build"),
    tag: str = typer.Option("latest", "--tag", "-t", help="Image tag"),
    push: bool = typer.Option(
        False, "--push", "-p", help="Push image to registry after building"
    ),
) -> None:
    """Build an image Docker image"""
    # Get image path
    image_path = config_manager.get_image_path(image_name)
    if not image_path:
        console.print(f"[red]Image '{image_name}' not found[/red]")
        return

    # Check if Dockerfile exists
    dockerfile_path = image_path / "Dockerfile"
    if not dockerfile_path.exists():
        console.print(f"[red]Dockerfile not found in {image_path}[/red]")
        return

    # Build image name
    docker_image_name = f"monadical/cubbi-{image_name}:{tag}"

    # Build the image
    with console.status(f"Building image {docker_image_name}..."):
        result = os.system(f"cd {image_path} && docker build -t {docker_image_name} .")

    if result != 0:
        console.print("[red]Failed to build image[/red]")
        return

    console.print(f"[green]Successfully built image: {docker_image_name}[/green]")

    # Push if requested
    if push:
        with console.status(f"Pushing image {docker_image_name}..."):
            result = os.system(f"docker push {docker_image_name}")

        if result != 0:
            console.print("[red]Failed to push image[/red]")
            return

        console.print(f"[green]Successfully pushed image: {docker_image_name}[/green]")


@image_app.command("info")
def image_info(
    image_name: str = typer.Argument(..., help="Image name to get info for"),
) -> None:
    """Show detailed information about an image"""
    image = config_manager.get_image(image_name)
    if not image:
        console.print(f"[red]Image '{image_name}' not found[/red]")
        return

    console.print(f"[bold]Image: {image.name}[/bold]")
    console.print(f"Description: {image.description}")
    console.print(f"Version: {image.version}")
    console.print(f"Maintainer: {image.maintainer}")
    console.print(f"Docker Image: {image.image}")

    if image.ports:
        console.print("\n[bold]Ports:[/bold]")
        for port in image.ports:
            console.print(f"  {port}")

    # Get image path
    image_path = config_manager.get_image_path(image_name)
    if image_path:
        console.print(f"\n[bold]Path:[/bold] {image_path}")

        # Check for README
        readme_path = image_path / "README.md"
        if readme_path.exists():
            console.print("\n[bold]README:[/bold]")
            with open(readme_path, "r") as f:
                console.print(f.read())


# Create a network subcommand for config
network_app = typer.Typer(help="Manage default networks")
config_app.add_typer(network_app, name="network", no_args_is_help=True)

# Create a volume subcommand for config
volume_app = typer.Typer(help="Manage default volumes")
config_app.add_typer(volume_app, name="volume", no_args_is_help=True)

# Create an MCP subcommand for config
config_mcp_app = typer.Typer(help="Manage default MCP servers")
config_app.add_typer(config_mcp_app, name="mcp", no_args_is_help=True)


# MCP configuration commands
@config_mcp_app.command("list")
def list_default_mcps() -> None:
    """List all default MCP servers"""
    default_mcps = user_config.get("defaults.mcps", [])

    if not default_mcps:
        console.print("No default MCP servers configured")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("MCP Server")

    for mcp in default_mcps:
        table.add_row(mcp)

    console.print(table)


@config_mcp_app.command("add")
def add_default_mcp(
    name: str = typer.Argument(..., help="MCP server name to add to defaults"),
) -> None:
    """Add an MCP server to default MCPs"""
    # First check if the MCP server exists
    mcp = mcp_manager.get_mcp(name)
    if not mcp:
        console.print(f"[red]MCP server '{name}' not found[/red]")
        return

    default_mcps = user_config.get("defaults.mcps", [])

    if name in default_mcps:
        console.print(f"MCP server '{name}' is already in defaults")
        return

    default_mcps.append(name)
    user_config.set("defaults.mcps", default_mcps)
    console.print(f"[green]Added MCP server '{name}' to defaults[/green]")


@config_mcp_app.command("remove")
def remove_default_mcp(
    name: str = typer.Argument(..., help="MCP server name to remove from defaults"),
) -> None:
    """Remove an MCP server from default MCPs"""
    default_mcps = user_config.get("defaults.mcps", [])

    if name not in default_mcps:
        console.print(f"MCP server '{name}' is not in defaults")
        return

    default_mcps.remove(name)
    user_config.set("defaults.mcps", default_mcps)
    console.print(f"[green]Removed MCP server '{name}' from defaults[/green]")


# Configuration commands
@config_app.command("list")
def list_config() -> None:
    """List all configuration values"""
    # Create table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Configuration", style="cyan")
    table.add_column("Value")

    # Add rows from flattened config
    for key, value in user_config.list_config():
        table.add_row(key, str(value))

    console.print(table)


@config_app.command("get")
def get_config(
    key: str = typer.Argument(
        ..., help="Configuration key to get (e.g., langfuse.url)"
    ),
) -> None:
    """Get a configuration value"""
    value = user_config.get(key)
    if value is None:
        console.print(f"[yellow]Configuration key '{key}' not found[/yellow]")
        return

    # Mask sensitive values
    if (
        any(substr in key.lower() for substr in ["key", "token", "secret", "password"])
        and value
    ):
        display_value = "*****"
    else:
        display_value = value

    console.print(f"{key} = {display_value}")


@config_app.command("set")
def set_config(
    key: str = typer.Argument(
        ..., help="Configuration key to set (e.g., langfuse.url)"
    ),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value"""
    try:
        # Convert string value to appropriate type
        if value.lower() == "true":
            typed_value = True
        elif value.lower() == "false":
            typed_value = False
        elif value.isdigit():
            typed_value = int(value)
        else:
            typed_value = value

        user_config.set(key, typed_value)

        # Mask sensitive values in output
        if (
            any(
                substr in key.lower()
                for substr in ["key", "token", "secret", "password"]
            )
            and value
        ):
            display_value = "*****"
        else:
            display_value = typed_value

        console.print(f"[green]Configuration updated: {key} = {display_value}[/green]")
    except Exception as e:
        console.print(f"[red]Error setting configuration: {e}[/red]")


@config_app.command("reset")
def reset_config(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Reset configuration to defaults"""
    if not confirm:
        should_reset = typer.confirm(
            "Are you sure you want to reset all configuration to defaults?"
        )
        if not should_reset:
            console.print("Reset canceled")
            return

    user_config.reset()
    console.print("[green]Configuration reset to defaults[/green]")


# Network configuration commands
@network_app.command("list")
def list_networks() -> None:
    """List all default networks"""
    networks = user_config.get("defaults.networks", [])

    if not networks:
        console.print("No default networks configured")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Network")

    for network in networks:
        table.add_row(network)

    console.print(table)


@network_app.command("add")
def add_network(
    network: str = typer.Argument(..., help="Network name to add to defaults"),
) -> None:
    """Add a network to default networks"""
    networks = user_config.get("defaults.networks", [])

    if network in networks:
        console.print(f"Network '{network}' is already in defaults")
        return

    networks.append(network)
    user_config.set("defaults.networks", networks)
    console.print(f"[green]Added network '{network}' to defaults[/green]")


@network_app.command("remove")
def remove_network(
    network: str = typer.Argument(..., help="Network name to remove from defaults"),
) -> None:
    """Remove a network from default networks"""
    networks = user_config.get("defaults.networks", [])

    if network not in networks:
        console.print(f"Network '{network}' is not in defaults")
        return

    networks.remove(network)
    user_config.set("defaults.networks", networks)
    console.print(f"[green]Removed network '{network}' from defaults[/green]")


# Volume configuration commands
@volume_app.command("list")
def list_volumes() -> None:
    """List all default volumes"""
    volumes = user_config.get("defaults.volumes", [])

    if not volumes:
        console.print("No default volumes configured")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Local Path")
    table.add_column("Container Path")

    for volume in volumes:
        if ":" in volume:
            local_path, container_path = volume.split(":", 1)
            table.add_row(local_path, container_path)
        else:
            table.add_row(volume, "[yellow]Invalid format[/yellow]")

    console.print(table)


@volume_app.command("add")
def add_volume(
    volume: str = typer.Argument(
        ..., help="Volume to add (format: LOCAL_PATH:CONTAINER_PATH)"
    ),
) -> None:
    """Add a volume to default volumes"""
    volumes = user_config.get("defaults.volumes", [])

    # Validate format
    if ":" not in volume:
        console.print(
            "[red]Invalid volume format. Use LOCAL_PATH:CONTAINER_PATH.[/red]"
        )
        return

    local_path, container_path = volume.split(":", 1)

    # Convert to absolute path if relative
    if not os.path.isabs(local_path):
        local_path = os.path.abspath(local_path)
        volume = f"{local_path}:{container_path}"

    # Validate local path exists
    if not os.path.exists(local_path):
        console.print(
            f"[yellow]Warning: Local path '{local_path}' does not exist.[/yellow]"
        )
        if not typer.confirm("Add anyway?"):
            return

    # Check if volume is already in defaults
    if volume in volumes:
        console.print(f"Volume '{volume}' is already in defaults")
        return

    volumes.append(volume)
    user_config.set("defaults.volumes", volumes)
    console.print(f"[green]Added volume '{volume}' to defaults[/green]")


@volume_app.command("remove")
def remove_volume(
    volume: str = typer.Argument(
        ..., help="Volume to remove (format: LOCAL_PATH:CONTAINER_PATH)"
    ),
) -> None:
    """Remove a volume from default volumes"""
    volumes = user_config.get("defaults.volumes", [])

    # Handle case where user provides just a prefix to match
    matching_volumes = [v for v in volumes if v.startswith(volume)]

    if not matching_volumes:
        console.print(f"No volumes matching '{volume}' found in defaults")
        return

    if len(matching_volumes) > 1:
        console.print(f"Multiple volumes match '{volume}':")
        for i, v in enumerate(matching_volumes):
            console.print(f"  {i + 1}. {v}")

        index = typer.prompt(
            "Enter the number of the volume to remove (0 to cancel)", type=int
        )
        if index == 0 or index > len(matching_volumes):
            console.print("Volume removal canceled")
            return

        volume_to_remove = matching_volumes[index - 1]
    else:
        volume_to_remove = matching_volumes[0]

    volumes.remove(volume_to_remove)
    user_config.set("defaults.volumes", volumes)
    console.print(f"[green]Removed volume '{volume_to_remove}' from defaults[/green]")


# MCP Management Commands


@mcp_app.command("list")
def list_mcps() -> None:
    """List all configured MCP servers"""
    mcps = mcp_manager.list_mcps()

    if not mcps:
        console.print("No MCP servers configured")
        return

    # Create a table with the MCP information
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Ports")
    table.add_column("Details")

    # Check status of each MCP
    for mcp in mcps:
        name = mcp.get("name", "")
        mcp_type = mcp.get("type", "")

        try:
            status_info = mcp_manager.get_mcp_status(name)
            status = status_info.get("status", "unknown")

            # Set status color based on status
            status_color = {
                "running": "green",
                "stopped": "red",
                "not_found": "yellow",
                "not_applicable": "blue",
                "failed": "red",
            }.get(status, "white")

            # Get port information
            ports_info = ""
            if mcp_type == "proxy" and status == "running":
                # For running proxy MCP, show the bound ports
                container_ports = status_info.get("ports", {})
                if container_ports:
                    port_mappings = []
                    for container_port, host_port in container_ports.items():
                        if host_port:
                            port_mappings.append(f"{host_port}←{container_port}")
                    if port_mappings:
                        ports_info = ", ".join(port_mappings)

            # For non-running proxy MCP, show the configured host port
            if not ports_info and mcp_type == "proxy" and mcp.get("host_port"):
                sse_port = mcp.get("proxy_options", {}).get("sse_port", 8080)
                ports_info = f"{mcp.get('host_port')}←{sse_port}/tcp (configured)"

            # Different details based on MCP type
            if mcp_type == "remote":
                details = mcp.get("url", "")
            elif mcp_type == "docker":
                details = mcp.get("image", "")
            elif mcp_type == "proxy":
                details = (
                    f"{mcp.get('base_image', '')} (via {mcp.get('proxy_image', '')})"
                )
            else:
                details = ""

            table.add_row(
                name,
                mcp_type,
                f"[{status_color}]{status}[/{status_color}]",
                ports_info,
                details,
            )
        except Exception as e:
            table.add_row(
                name,
                mcp_type,
                "[red]error[/red]",
                "",  # Empty ports column for error
                str(e),
            )

    console.print(table)


@mcp_app.command("status")
def mcp_status(name: str = typer.Argument(..., help="MCP server name")) -> None:
    """Show detailed status of an MCP server"""
    try:
        # Get the MCP configuration
        mcp_config = mcp_manager.get_mcp(name)
        if not mcp_config:
            console.print(f"[red]MCP server '{name}' not found[/red]")
            return

        # Get status information
        status_info = mcp_manager.get_mcp_status(name)

        # Print detailed information
        console.print(f"[bold]MCP Server:[/bold] {name}")
        console.print(f"[bold]Type:[/bold] {mcp_config.get('type')}")

        status = status_info.get("status")
        status_color = {
            "running": "green",
            "stopped": "red",
            "not_found": "yellow",
            "not_applicable": "blue",
            "failed": "red",
        }.get(status, "white")

        console.print(f"[bold]Status:[/bold] [{status_color}]{status}[/{status_color}]")

        # Type-specific information
        if mcp_config.get("type") == "remote":
            console.print(f"[bold]URL:[/bold] {mcp_config.get('url')}")
            if mcp_config.get("headers"):
                console.print("[bold]Headers:[/bold]")
                for key, value in mcp_config.get("headers", {}).items():
                    # Mask sensitive headers
                    if (
                        "token" in key.lower()
                        or "key" in key.lower()
                        or "auth" in key.lower()
                    ):
                        console.print(f"  {key}: ****")
                    else:
                        console.print(f"  {key}: {value}")

        elif mcp_config.get("type") in ["docker", "proxy"]:
            console.print(f"[bold]Image:[/bold] {status_info.get('image')}")
            if status_info.get("container_id"):
                console.print(
                    f"[bold]Container ID:[/bold] {status_info.get('container_id')}"
                )
            if status_info.get("ports"):
                console.print("[bold]Container Ports:[/bold]")
                for port, host_port in status_info.get("ports", {}).items():
                    if host_port:
                        console.print(
                            f"  {port} -> [green]bound to host port {host_port}[/green]"
                        )
                    else:
                        console.print(f"  {port} (internal only)")
            if status_info.get("created"):
                console.print(f"[bold]Created:[/bold] {status_info.get('created')}")

            # For proxy type, show additional information
            if mcp_config.get("type") == "proxy":
                console.print(
                    f"[bold]Base Image:[/bold] {mcp_config.get('base_image')}"
                )
                console.print(
                    f"[bold]Proxy Image:[/bold] {mcp_config.get('proxy_image')}"
                )

                # Show configured host port binding
                if mcp_config.get("host_port"):
                    sse_port = mcp_config.get("proxy_options", {}).get("sse_port", 8080)
                    console.print(
                        f"[bold]Port Binding:[/bold] Container port {sse_port}/tcp -> Host port {mcp_config.get('host_port')}"
                    )

                console.print("[bold]Proxy Options:[/bold]")
                for key, value in mcp_config.get("proxy_options", {}).items():
                    console.print(f"  {key}: {value}")

    except Exception as e:
        console.print(f"[red]Error getting MCP status: {e}[/red]")


@mcp_app.command("start")
def start_mcp(
    name: Optional[str] = typer.Argument(None, help="MCP server name"),
    all_servers: bool = typer.Option(False, "--all", help="Start all MCP servers"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Start an MCP server or all servers"""
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Check if we need to start all servers
    if all_servers:
        # Get all configured MCP servers
        mcps = mcp_manager.list_mcps()

        if not mcps:
            console.print("[yellow]No MCP servers configured[/yellow]")
            return

        # Count of successfully started servers
        started_count = 0
        remote_count = 0
        failed_count = 0

        console.print(f"Starting {len(mcps)} MCP servers...")

        # Keep track of MCP container names that were successfully started
        mcp_container_names = []

        for mcp in mcps:
            mcp_name = mcp.get("name")
            if not mcp_name:
                continue

            try:
                with console.status(f"Starting MCP server '{mcp_name}'..."):
                    result = mcp_manager.start_mcp(mcp_name)
                    container_name = mcp_manager.get_mcp_container_name(mcp_name)
                    mcp_container_names.append(container_name)

                if result.get("status") == "running":
                    console.print(f"[green]Started MCP server '{mcp_name}'[/green]")
                    started_count += 1
                elif result.get("status") == "not_applicable":
                    console.print(
                        f"[blue]MCP server '{mcp_name}' is a remote type (no container to start)[/blue]"
                    )
                    remote_count += 1
                else:
                    console.print(
                        f"MCP server '{mcp_name}' status: {result.get('status')}"
                    )
                    failed_count += 1
            except Exception as e:
                console.print(f"[red]Error starting MCP server '{mcp_name}': {e}[/red]")
                # Remove from the container names list if failed
                if container_name in mcp_container_names:
                    mcp_container_names.remove(container_name)
                failed_count += 1

        # Show a summary
        if started_count > 0:
            console.print(
                f"[green]Successfully started {started_count} MCP servers[/green]"
            )
        if remote_count > 0:
            console.print(
                f"[blue]{remote_count} remote MCP servers (no action needed)[/blue]"
            )
        if failed_count > 0:
            console.print(f"[red]Failed to start {failed_count} MCP servers[/red]")

    # Otherwise start a specific server
    elif name:
        try:
            with console.status(f"Starting MCP server '{name}'..."):
                result = mcp_manager.start_mcp(name)

            if result.get("status") == "running":
                console.print(f"[green]Started MCP server '{name}'[/green]")
            elif result.get("status") == "not_applicable":
                console.print(
                    f"[blue]MCP server '{name}' is a remote type (no container to start)[/blue]"
                )
            else:
                console.print(f"MCP server '{name}' status: {result.get('status')}")

        except Exception as e:
            console.print(f"[red]Error starting MCP server: {e}[/red]")
    else:
        console.print(
            "[red]Error: Please provide a server name or use --all to start all servers[/red]"
        )


@mcp_app.command("stop")
def stop_mcp(
    name: Optional[str] = typer.Argument(None, help="MCP server name"),
    all_servers: bool = typer.Option(False, "--all", help="Stop all MCP servers"),
) -> None:
    """Stop an MCP server or all servers"""
    # Check if we need to stop all servers
    if all_servers:
        # Get all configured MCP servers
        mcps = mcp_manager.list_mcps()

        if not mcps:
            console.print("[yellow]No MCP servers configured[/yellow]")
            return

        # Count of successfully stopped servers
        stopped_count = 0
        not_running_count = 0
        failed_count = 0

        console.print(f"Stopping and removing {len(mcps)} MCP servers...")

        for mcp in mcps:
            mcp_name = mcp.get("name")
            if not mcp_name:
                continue

            try:
                with console.status(
                    f"Stopping and removing MCP server '{mcp_name}'..."
                ):
                    result = mcp_manager.stop_mcp(mcp_name)

                if result:
                    console.print(
                        f"[green]Stopped and removed MCP server '{mcp_name}'[/green]"
                    )
                    stopped_count += 1
                else:
                    console.print(
                        f"[yellow]MCP server '{mcp_name}' was not running or doesn't exist[/yellow]"
                    )
                    not_running_count += 1
            except Exception as e:
                console.print(
                    f"[red]Error stopping/removing MCP server '{mcp_name}': {e}[/red]"
                )
                failed_count += 1

        # Show a summary
        if stopped_count > 0:
            console.print(
                f"[green]Successfully stopped and removed {stopped_count} MCP servers[/green]"
            )
        if not_running_count > 0:
            console.print(
                f"[yellow]{not_running_count} MCP servers were not running[/yellow]"
            )
        if failed_count > 0:
            console.print(f"[red]Failed to stop {failed_count} MCP servers[/red]")

    # Otherwise stop a specific server
    elif name:
        try:
            with console.status(f"Stopping and removing MCP server '{name}'..."):
                result = mcp_manager.stop_mcp(name)

            if result:
                console.print(f"[green]Stopped and removed MCP server '{name}'[/green]")
            else:
                console.print(
                    f"[yellow]MCP server '{name}' was not running or doesn't exist[/yellow]"
                )

        except Exception as e:
            console.print(f"[red]Error stopping/removing MCP server: {e}[/red]")
    else:
        console.print(
            "[red]Error: Please provide a server name or use --all to stop all servers[/red]"
        )


@mcp_app.command("restart")
def restart_mcp(
    name: Optional[str] = typer.Argument(None, help="MCP server name"),
    all_servers: bool = typer.Option(False, "--all", help="Restart all MCP servers"),
) -> None:
    """Restart an MCP server or all servers"""
    # Check if we need to restart all servers
    if all_servers:
        # Get all configured MCP servers
        mcps = mcp_manager.list_mcps()

        if not mcps:
            console.print("[yellow]No MCP servers configured[/yellow]")
            return

        # Count of successfully restarted servers
        restarted_count = 0
        remote_count = 0
        failed_count = 0

        console.print(f"Restarting {len(mcps)} MCP servers...")

        for mcp in mcps:
            mcp_name = mcp.get("name")
            if not mcp_name:
                continue

            try:
                with console.status(f"Restarting MCP server '{mcp_name}'..."):
                    result = mcp_manager.restart_mcp(mcp_name)

                if result.get("status") == "running":
                    console.print(f"[green]Restarted MCP server '{mcp_name}'[/green]")
                    restarted_count += 1
                elif result.get("status") == "not_applicable":
                    console.print(
                        f"[blue]MCP server '{mcp_name}' is a remote type (no container to restart)[/blue]"
                    )
                    remote_count += 1
                else:
                    console.print(
                        f"MCP server '{mcp_name}' status: {result.get('status')}"
                    )
                    failed_count += 1
            except Exception as e:
                console.print(
                    f"[red]Error restarting MCP server '{mcp_name}': {e}[/red]"
                )
                failed_count += 1

        # Show a summary
        if restarted_count > 0:
            console.print(
                f"[green]Successfully restarted {restarted_count} MCP servers[/green]"
            )
        if remote_count > 0:
            console.print(
                f"[blue]{remote_count} remote MCP servers (no action needed)[/blue]"
            )
        if failed_count > 0:
            console.print(f"[red]Failed to restart {failed_count} MCP servers[/red]")

    # Otherwise restart a specific server
    elif name:
        try:
            with console.status(f"Restarting MCP server '{name}'..."):
                result = mcp_manager.restart_mcp(name)

            if result.get("status") == "running":
                console.print(f"[green]Restarted MCP server '{name}'[/green]")
            elif result.get("status") == "not_applicable":
                console.print(
                    f"[blue]MCP server '{name}' is a remote type (no container to restart)[/blue]"
                )
            else:
                console.print(f"MCP server '{name}' status: {result.get('status')}")

        except Exception as e:
            console.print(f"[red]Error restarting MCP server: {e}[/red]")
    else:
        console.print(
            "[red]Error: Please provide a server name or use --all to restart all servers[/red]"
        )


@mcp_app.command("logs")
def mcp_logs(
    name: str = typer.Argument(..., help="MCP server name"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show"),
) -> None:
    """Show logs from an MCP server"""
    try:
        logs = mcp_manager.get_mcp_logs(name, tail=tail)
        console.print(logs)

    except Exception as e:
        console.print(f"[red]Error getting MCP logs: {e}[/red]")


@mcp_app.command("remove")
def remove_mcp(name: str = typer.Argument(..., help="MCP server name")) -> None:
    """Remove an MCP server configuration"""
    try:
        # Check if any active sessions might be using this MCP
        active_sessions = container_manager.list_sessions()
        affected_sessions = []

        for session in active_sessions:
            if session.mcps and name in session.mcps:
                affected_sessions.append(session)

        # Just warn users about affected sessions
        if affected_sessions:
            console.print(
                f"[yellow]Warning: Found {len(affected_sessions)} active sessions using MCP '{name}'[/yellow]"
            )
            console.print(
                "[yellow]You may need to restart these sessions for changes to take effect:[/yellow]"
            )
            for session in affected_sessions:
                console.print(f"  - Session: {session.id} ({session.name})")

        # Remove the MCP from configuration
        with console.status(f"Removing MCP server '{name}'..."):
            result = mcp_manager.remove_mcp(name)

        if result:
            console.print(f"[green]Removed MCP server '{name}'[/green]")
        else:
            console.print(f"[yellow]MCP server '{name}' not found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error removing MCP server: {e}[/red]")


@mcp_app.command("add")
def add_mcp(
    name: str = typer.Argument(..., help="MCP server name"),
    base_image: str = typer.Argument(..., help="Base MCP Docker image"),
    proxy_image: str = typer.Option(
        "ghcr.io/sparfenyuk/mcp-proxy:latest",
        "--proxy-image",
        help="Proxy image for MCP",
    ),
    command: str = typer.Option(
        "", "--command", "-c", help="Command to run in the container"
    ),
    sse_port: int = typer.Option(
        8080, "--sse-port", help="Port for SSE server inside container"
    ),
    sse_host: str = typer.Option("0.0.0.0", "--sse-host", help="Host for SSE server"),
    allow_origin: str = typer.Option(
        "*", "--allow-origin", help="CORS allow-origin header"
    ),
    host_port: Optional[int] = typer.Option(
        None,
        "--host-port",
        "-p",
        help="Host port to bind the MCP server to (auto-assigned if not specified)",
    ),
    env: List[str] = typer.Option(
        [], "--env", "-e", help="Environment variables (format: KEY=VALUE)"
    ),
    no_default: bool = typer.Option(
        False, "--no-default", help="Don't add MCP server to defaults"
    ),
) -> None:
    """Add a proxy-based MCP server (default type)"""
    # Parse environment variables
    environment = {}
    for var in env:
        if "=" in var:
            key, value = var.split("=", 1)
            environment[key] = value
        else:
            console.print(
                f"[yellow]Warning: Ignoring invalid environment variable format: {var}[/yellow]"
            )

    # Prepare proxy options
    proxy_options = {
        "sse_port": sse_port,
        "sse_host": sse_host,
        "allow_origin": allow_origin,
    }

    try:
        with console.status(f"Adding MCP server '{name}'..."):
            result = mcp_manager.add_proxy_mcp(
                name,
                base_image,
                proxy_image,
                command,
                proxy_options,
                environment,
                host_port,
                add_as_default=not no_default,
            )

            # Get the assigned port
            assigned_port = result.get("host_port")

        console.print(f"[green]Added MCP server '{name}'[/green]")
        if assigned_port:
            console.print(
                f"Container port {sse_port} will be bound to host port {assigned_port}"
            )

        if not no_default:
            console.print(f"MCP server '{name}' added to defaults")
        else:
            console.print(f"MCP server '{name}' not added to defaults")

    except Exception as e:
        console.print(f"[red]Error adding MCP server: {e}[/red]")


@mcp_app.command("add-remote")
def add_remote_mcp(
    name: str = typer.Argument(..., help="MCP server name"),
    url: str = typer.Argument(..., help="URL of the remote MCP server"),
    header: List[str] = typer.Option(
        [], "--header", "-H", help="HTTP headers (format: KEY=VALUE)"
    ),
    no_default: bool = typer.Option(
        False, "--no-default", help="Don't add MCP server to defaults"
    ),
) -> None:
    """Add a remote MCP server"""
    # Parse headers
    headers = {}
    for h in header:
        if "=" in h:
            key, value = h.split("=", 1)
            headers[key] = value
        else:
            console.print(
                f"[yellow]Warning: Ignoring invalid header format: {h}[/yellow]"
            )

    try:
        with console.status(f"Adding remote MCP server '{name}'..."):
            mcp_manager.add_remote_mcp(
                name, url, headers, add_as_default=not no_default
            )

        console.print(f"[green]Added remote MCP server '{name}'[/green]")

        if not no_default:
            console.print(f"MCP server '{name}' added to defaults")
        else:
            console.print(f"MCP server '{name}' not added to defaults")

    except Exception as e:
        console.print(f"[red]Error adding remote MCP server: {e}[/red]")


@mcp_app.command("inspector")
def run_mcp_inspector(
    client_port: int = typer.Option(
        5173,
        "--client-port",
        "-c",
        help="Port for the MCP Inspector frontend (default: 5173)",
    ),
    server_port: int = typer.Option(
        3000,
        "--server-port",
        "-s",
        help="Port for the MCP Inspector backend API (default: 3000)",
    ),
    detach: bool = typer.Option(False, "--detach", "-d", help="Run in detached mode"),
    stop: bool = typer.Option(False, "--stop", help="Stop running MCP Inspector(s)"),
) -> None:
    """Run the MCP Inspector to visualize and debug MCP servers"""
    import docker
    import time

    # Get Docker client quietly
    try:
        client = docker.from_env()
    except Exception as e:
        console.print(f"[red]Error connecting to Docker: {e}[/red]")
        return

    # If stop flag is set, stop all running MCP Inspectors
    if stop:
        containers = client.containers.list(
            all=True, filters={"label": "cubbi.mcp.inspector=true"}
        )
        if not containers:
            console.print("[yellow]No running MCP Inspector instances found[/yellow]")
            return

        with console.status("Stopping MCP Inspector..."):
            for container in containers:
                try:
                    container.stop()
                    container.remove(force=True)
                except Exception:
                    pass

        console.print("[green]MCP Inspector stopped[/green]")
        return

    # Check if inspector is already running
    all_inspectors = client.containers.list(
        all=True, filters={"label": "cubbi.mcp.inspector=true"}
    )

    # Stop any existing inspectors first
    for inspector in all_inspectors:
        try:
            if inspector.status == "running":
                inspector.stop(timeout=1)
            inspector.remove(force=True)
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not remove existing inspector: {e}[/yellow]"
            )

    # Check if the specified ports are already in use
    import socket

    # Check client port
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.bind(("0.0.0.0", client_port))
        client_socket.close()
    except socket.error:
        console.print(
            f"[red]Error: Client port {client_port} is already in use by another process.[/red]"
        )
        console.print("Please stop any web servers or other processes using this port.")
        console.print("You can try a different client port with --client-port option")
        return

    # Check server port
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind(("0.0.0.0", server_port))
        server_socket.close()
    except socket.error:
        console.print(
            f"[red]Error: Server port {server_port} is already in use by another process.[/red]"
        )
        console.print("Please stop any web servers or other processes using this port.")
        console.print("You can try a different server port with --server-port option")
        return

    # Container name with timestamp to avoid conflicts
    container_name = f"cubbi_mcp_inspector_{int(time.time())}"

    with console.status("Starting MCP Inspector..."):
        # Get MCP servers from configuration
        all_mcps = mcp_manager.list_mcps()

        # Get all MCP server URLs (including remote ones)
        mcp_servers = []

        # Collect networks that need to be connected to the Inspector
        mcp_networks_to_connect = []

        # Add remote MCP servers
        for mcp in all_mcps:
            if mcp.get("type") == "remote":
                url = mcp.get("url", "")
                headers = mcp.get("headers", {})
                if url:
                    mcp_servers.append(
                        {
                            "name": mcp.get("name", "Remote MCP"),
                            "url": url,
                            "headers": headers,
                        }
                    )

        # Process container-based MCP servers from the configuration
        for mcp in all_mcps:
            # We only need to connect to container-based MCPs
            if mcp.get("type") in ["docker", "proxy"]:
                mcp_name = mcp.get("name")
                try:
                    # Get the container name for this MCP
                    container_name = f"cubbi_mcp_{mcp_name}"
                    container = None

                    # Try to find the container
                    try:
                        container = client.containers.get(container_name)
                    except docker.errors.NotFound:
                        console.print(
                            f"[yellow]Warning: Container for MCP '{mcp_name}' not found[/yellow]"
                        )
                        continue

                    if container and container.status == "running":
                        # Find all networks this MCP container is connected to
                        for network_name, network_info in (
                            container.attrs.get("NetworkSettings", {})
                            .get("Networks", {})
                            .items()
                        ):
                            # Don't add default bridge network - it doesn't support DNS resolution
                            # Also avoid duplicate networks
                            if (
                                network_name != "bridge"
                                and network_name not in mcp_networks_to_connect
                            ):
                                mcp_networks_to_connect.append(network_name)

                        # For proxy type, get the SSE port from the config
                        port = "8080"  # Default MCP proxy SSE port
                        if mcp.get("type") == "proxy" and "proxy_options" in mcp:
                            port = str(
                                mcp.get("proxy_options", {}).get("sse_port", "8080")
                            )

                        # Add container-based MCP server URL using just the MCP name as the hostname
                        # This works because we join all networks and the MCP containers have aliases
                        mcp_servers.append(
                            {
                                "name": mcp_name,
                                "url": f"http://{mcp_name}:{port}",
                                "headers": {},
                            }
                        )
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Error processing MCP '{mcp_name}': {str(e)}[/yellow]"
                    )

        # Make sure we have at least one network to connect to
        if not mcp_networks_to_connect:
            # Create an MCP-specific network if none exists
            network_name = "cubbi-mcp-network"
            console.print("No MCP networks found, creating a default one")
            try:
                networks = client.networks.list(names=[network_name])
                if not networks:
                    client.networks.create(network_name, driver="bridge")
                mcp_networks_to_connect.append(network_name)
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not create default network: {str(e)}[/yellow]"
                )

        # Pull the image if needed (silently)
        try:
            client.images.get("mcp/inspector")
        except docker.errors.ImageNotFound:
            client.images.pull("mcp/inspector")

        try:
            # Create a custom entrypoint to handle the localhost binding issue and auto-connect to MCP servers
            script_content = """#!/bin/sh
# This script modifies the Express server to bind to all interfaces

# Try to find the CLI script
CLI_FILE=$(find /app -name "cli.js" | grep -v node_modules | head -1)

if [ -z "$CLI_FILE" ]; then
  echo "Could not find CLI file. Trying common locations..."
  for path in "/app/client/bin/cli.js" "/app/bin/cli.js" "./client/bin/cli.js" "./bin/cli.js"; do
    if [ -f "$path" ]; then
      CLI_FILE="$path"
      break
    fi
  done
fi

if [ -z "$CLI_FILE" ]; then
  echo "ERROR: Could not find the MCP Inspector CLI file."
  exit 1
fi

echo "Found CLI file at: $CLI_FILE"

# Make a backup of the original file
cp "$CLI_FILE" "$CLI_FILE.bak"

# Modify the file to use 0.0.0.0 as the host
sed -i 's/app.listen(PORT/app.listen(PORT, "0.0.0.0"/g' "$CLI_FILE"
sed -i 's/server.listen(port/server.listen(port, "0.0.0.0"/g' "$CLI_FILE"
sed -i 's/listen(PORT/listen(PORT, "0.0.0.0"/g' "$CLI_FILE"

echo "Modified server to listen on all interfaces (0.0.0.0)"

# Start the MCP Inspector
echo "Starting MCP Inspector on all interfaces..."
exec npm start
"""

            # Write the script to a temp file
            script_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "cubbi_inspector_entrypoint.sh",
            )
            with open(script_path, "w") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)

            # Use the script as the entrypoint
            # The entrypoint is directly specified in the container.run() call below

            # Run the MCP Inspector container - use the first network initially
            initial_network = (
                mcp_networks_to_connect[0] if mcp_networks_to_connect else "bridge"
            )
            console.print(f"Starting Inspector on network: {initial_network}")

            # Check if existing container with the same name exists, and remove it
            try:
                existing = client.containers.get("cubbi_mcp_inspector")
                if existing.status == "running":
                    existing.stop(timeout=1)
                existing.remove(force=True)
                console.print("Removed existing MCP Inspector container")
            except docker.errors.NotFound:
                pass
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Error removing existing container: {e}[/yellow]"
                )

            # Create network config with just the inspector alias for the initial network
            network_config = {
                initial_network: {
                    "aliases": [
                        "inspector"
                    ]  # Allow container to be reached as just "inspector"
                }
            }

            # Log MCP servers that are in the initial network
            initial_mcp_containers = []
            for mcp in all_mcps:
                if mcp.get("type") in ["docker", "proxy"]:
                    mcp_name = mcp.get("name")
                    container_name = f"cubbi_mcp_{mcp_name}"

                    try:
                        # Check if this container exists
                        mcp_container = client.containers.get(container_name)
                        # Check if it's in the initial network
                        if initial_network in mcp_container.attrs.get(
                            "NetworkSettings", {}
                        ).get("Networks", {}):
                            initial_mcp_containers.append(mcp_name)
                    except Exception:
                        pass

            if initial_mcp_containers:
                console.print(
                    f"MCP servers in initial network: {', '.join(initial_mcp_containers)}"
                )

            container = client.containers.run(
                image="mcp/inspector",
                name="cubbi_mcp_inspector",  # Use a fixed name
                detach=True,
                network=initial_network,
                ports={
                    f"{client_port}/tcp": client_port,  # Map container port to host port (frontend)
                    f"{server_port}/tcp": server_port,  # Map container port to host port (backend)
                },
                environment={
                    "CLIENT_PORT": str(
                        client_port
                    ),  # Tell the client to use the client_port
                    "SERVER_PORT": str(
                        server_port
                    ),  # Tell the server to use the server_port
                },
                volumes={
                    script_path: {
                        "bind": "/entrypoint.sh",
                        "mode": "ro",
                    }
                },
                entrypoint="/entrypoint.sh",
                labels={
                    "cubbi.mcp.inspector": "true",
                    "cubbi.managed": "true",
                },
                network_mode=None,  # Don't use network_mode as we're using network with aliases
                networking_config=client.api.create_networking_config(network_config),
            )

            # Connect to all additional MCP networks
            if len(mcp_networks_to_connect) > 1:
                # Get the networks the container is already connected to
                container_networks = list(
                    container.attrs["NetworkSettings"]["Networks"].keys()
                )

                for network_name in mcp_networks_to_connect[
                    1:
                ]:  # Skip the first one that we already connected to
                    # Skip if already connected to this network
                    if network_name in container_networks:
                        console.print(
                            f"Inspector already connected to network: {network_name}"
                        )
                        continue

                    try:
                        console.print(
                            f"Connecting Inspector to additional network: {network_name}"
                        )
                        network = client.networks.get(network_name)

                        # Get all MCP containers in this network
                        mcp_containers = []

                        # Find all MCP containers that are in this network
                        for mcp in all_mcps:
                            if mcp.get("type") in ["docker", "proxy"]:
                                mcp_name = mcp.get("name")
                                container_name = f"cubbi_mcp_{mcp_name}"

                                try:
                                    # Check if this container exists
                                    mcp_container = client.containers.get(
                                        container_name
                                    )
                                    # Check if it's in the current network
                                    if network_name in mcp_container.attrs.get(
                                        "NetworkSettings", {}
                                    ).get("Networks", {}):
                                        mcp_containers.append(mcp_name)
                                except Exception:
                                    pass

                        # Connect the inspector with the inspector alias and the individual MCP server aliases
                        network.connect(container, aliases=["inspector"])
                        console.print(f"  Added inspector to network {network_name}")

                        if mcp_containers:
                            console.print(
                                f"  MCP servers in this network: {', '.join(mcp_containers)}"
                            )
                    except Exception as e:
                        console.print(
                            f"[yellow]Warning: Could not connect Inspector to network {network_name}: {str(e)}[/yellow]"
                        )

            # Wait a moment for the container to start properly
            time.sleep(1)

        except Exception as e:
            console.print(f"[red]Error running MCP Inspector: {e}[/red]")
            # Try to clean up
            try:
                client.containers.get(container_name).remove(force=True)
            except Exception:
                pass
            return

    console.print("[bold]MCP Inspector is available at:[/bold]")
    console.print(f"- Frontend: http://localhost:{client_port}")
    console.print(f"- Backend API: http://localhost:{server_port}")

    if len(mcp_servers) > 0:
        console.print(
            f"[green]Auto-connected to {len(mcp_servers)} MCP servers[/green]"
        )

        # Print MCP server URLs for access within the Inspector
        console.print("[bold]MCP Server URLs (for use within Inspector):[/bold]")
        for mcp in all_mcps:
            mcp_name = mcp.get("name")
            mcp_type = mcp.get("type")

            if mcp_type in ["docker", "proxy"]:
                # For container-based MCPs, use the container name as hostname
                # Default SSE port is 8080 unless specified in proxy_options
                sse_port = "8080"
                if mcp_type == "proxy" and "proxy_options" in mcp:
                    sse_port = str(mcp.get("proxy_options", {}).get("sse_port", "8080"))
                console.print(f"- {mcp_name}: http://{mcp_name}:{sse_port}/sse")
            elif mcp_type == "remote":
                # For remote MCPs, use the configured URL
                mcp_url = mcp.get("url")
                if mcp_url:
                    console.print(f"- {mcp_name}: {mcp_url}")
    else:
        console.print(
            "[yellow]Warning: No MCP servers found or started. The Inspector will run but won't have any servers to connect to.[/yellow]"
        )
        console.print(
            "Start MCP servers using 'cubbi mcp start --all' and then restart the Inspector."
        )

    if not detach:
        try:
            console.print("[yellow]Press Ctrl+C to stop the MCP Inspector...[/yellow]")
            for line in container.logs(stream=True):
                console.print(line.decode().strip())
        except KeyboardInterrupt:
            with console.status("Stopping MCP Inspector..."):
                container.stop()
                container.remove(force=True)
            console.print("[green]MCP Inspector stopped[/green]")


def session_create_entry_point():
    """Entry point that directly invokes 'cubbi session create'.

    This provides a convenient shortcut:
    - 'cubbix' runs as if you typed 'cubbi session create'
    - 'cubbix .' mounts the current directory
    - 'cubbix /path/to/project' mounts the specified directory
    - 'cubbix repo-url' clones the repository

    All command-line options are passed through to 'session create'.
    """
    import sys

    # Save the program name (e.g., 'cubbix')
    prog_name = sys.argv[0]
    # Insert 'session' and 'create' commands before any other arguments
    sys.argv.insert(1, "session")
    sys.argv.insert(2, "create")
    # Run the app with the modified arguments
    app(prog_name=prog_name)


if __name__ == "__main__":
    app()
