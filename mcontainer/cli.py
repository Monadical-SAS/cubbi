import os
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigManager
from .container import ContainerManager
from .models import SessionStatus
from .user_config import UserConfigManager

app = typer.Typer(help="Monadical Container Tool")
session_app = typer.Typer(help="Manage MC sessions")
driver_app = typer.Typer(help="Manage MC drivers", no_args_is_help=True)
config_app = typer.Typer(help="Manage MC configuration")
app.add_typer(session_app, name="session", no_args_is_help=True)
app.add_typer(driver_app, name="driver", no_args_is_help=True)
app.add_typer(config_app, name="config", no_args_is_help=True)

console = Console()
config_manager = ConfigManager()
user_config = UserConfigManager()
container_manager = ContainerManager(config_manager)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Monadical Container Tool"""
    # If no command is specified, create a session
    if ctx.invoked_subcommand is None:
        create_session(
            driver=None,
            project=None,
            env=[],
            volume=[],
            name=None,
            no_connect=False,
            no_mount=False,
        )


@app.command()
def version() -> None:
    """Show MC version information"""
    from importlib.metadata import version as get_version

    try:
        version_str = get_version("mcontainer")
        console.print(f"MC - Monadical Container Tool v{version_str}")
    except Exception:
        console.print("MC - Monadical Container Tool (development version)")


@session_app.command("list")
def list_sessions() -> None:
    """List active MC sessions"""
    sessions = container_manager.list_sessions()

    if not sessions:
        console.print("No active sessions found")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Driver")
    table.add_column("Status")
    table.add_column("Ports")
    table.add_column("Project")

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
            session.driver,
            f"[{status_color}]{status_name}[/{status_color}]",
            ports_str,
            session.project or "",
        )

    console.print(table)


@session_app.command("create")
def create_session(
    driver: Optional[str] = typer.Option(None, "--driver", "-d", help="Driver to use"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project repository URL"
    ),
    env: List[str] = typer.Option(
        [], "--env", "-e", help="Environment variables (KEY=VALUE)"
    ),
    volume: List[str] = typer.Option(
        [], "--volume", "-v", help="Mount volumes (LOCAL_PATH:CONTAINER_PATH)"
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Session name"),
    no_connect: bool = typer.Option(
        False, "--no-connect", help="Don't automatically connect to the session"
    ),
    no_mount: bool = typer.Option(
        False,
        "--no-mount",
        help="Don't mount local directory to /app (ignored if --project is used)",
    ),
) -> None:
    """Create a new MC session"""
    # Use default driver from user configuration
    if not driver:
        driver = user_config.get(
            "defaults.driver", config_manager.config.defaults.get("driver", "goose")
        )

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
    for vol in volume:
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

            # Add to volume mounts
            volume_mounts[local_path] = {"bind": container_path, "mode": "rw"}
        else:
            console.print(
                f"[yellow]Warning: Ignoring invalid volume format: {vol}. Use LOCAL_PATH:CONTAINER_PATH.[/yellow]"
            )

    with console.status(f"Creating session with driver '{driver}'..."):
        session = container_manager.create_session(
            driver_name=driver,
            project=project,
            environment=environment,
            session_name=name,
            mount_local=not no_mount and user_config.get("defaults.mount_local", True),
            volumes=volume_mounts,
        )

    if session:
        console.print("[green]Session created successfully![/green]")
        console.print(f"Session ID: {session.id}")
        console.print(f"Driver: {session.driver}")

        if session.ports:
            console.print("Ports:")
            for container_port, host_port in session.ports.items():
                console.print(f"  {container_port} -> {host_port}")

        # Auto-connect based on user config, unless overridden by --no-connect flag
        auto_connect = user_config.get("defaults.connect", True)
        if not no_connect and auto_connect:
            container_manager.connect_session(session.id)
        else:
            console.print(
                f"\nConnect to the session with:\n  mc session connect {session.id}"
            )
    else:
        console.print("[red]Failed to create session[/red]")


@session_app.command("close")
def close_session(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to close"),
    all_sessions: bool = typer.Option(False, "--all", help="Close all active sessions"),
) -> None:
    """Close a MC session or all sessions"""
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
    """Connect to a MC session"""
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
    """Stream logs from a MC session"""
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


@app.command()
def stop() -> None:
    """Stop the current MC session (from inside the container)"""
    # Check if running inside a container
    if not os.path.exists("/.dockerenv"):
        console.print(
            "[red]This command can only be run from inside a MC container[/red]"
        )
        return

    # Stop the container from inside
    console.print("Stopping the current session...")
    os.system("kill 1")  # Send SIGTERM to PID 1 (container's init process)


# Main CLI entry point that handles project repository URLs
@app.command(name="")
def quick_create(
    project: Optional[str] = typer.Argument(..., help="Project repository URL"),
    driver: Optional[str] = typer.Option(None, "--driver", "-d", help="Driver to use"),
    env: List[str] = typer.Option(
        [], "--env", "-e", help="Environment variables (KEY=VALUE)"
    ),
    volume: List[str] = typer.Option(
        [], "--volume", "-v", help="Mount volumes (LOCAL_PATH:CONTAINER_PATH)"
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Session name"),
    no_connect: bool = typer.Option(
        False, "--no-connect", help="Don't automatically connect to the session"
    ),
    no_mount: bool = typer.Option(
        False,
        "--no-mount",
        help="Don't mount local directory to /app (ignored if a project is specified)",
    ),
) -> None:
    """Create a new MC session with a project repository"""
    # Use user config for defaults if not specified
    if not driver:
        driver = user_config.get("defaults.driver")

    create_session(
        driver=driver,
        project=project,
        env=env,
        volume=volume,
        name=name,
        no_connect=no_connect,
        no_mount=no_mount,
    )


@driver_app.command("list")
def list_drivers() -> None:
    """List available MC drivers"""
    drivers = config_manager.list_drivers()

    if not drivers:
        console.print("No drivers found")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Version")
    table.add_column("Maintainer")
    table.add_column("Image")

    for name, driver in drivers.items():
        table.add_row(
            driver.name,
            driver.description,
            driver.version,
            driver.maintainer,
            driver.image,
        )

    console.print(table)


@driver_app.command("build")
def build_driver(
    driver_name: str = typer.Argument(..., help="Driver name to build"),
    tag: str = typer.Option("latest", "--tag", "-t", help="Image tag"),
    push: bool = typer.Option(
        False, "--push", "-p", help="Push image to registry after building"
    ),
) -> None:
    """Build a driver Docker image"""
    # Get driver path
    driver_path = config_manager.get_driver_path(driver_name)
    if not driver_path:
        console.print(f"[red]Driver '{driver_name}' not found[/red]")
        return

    # Check if Dockerfile exists
    dockerfile_path = driver_path / "Dockerfile"
    if not dockerfile_path.exists():
        console.print(f"[red]Dockerfile not found in {driver_path}[/red]")
        return

    # Build image name
    image_name = f"monadical/mc-{driver_name}:{tag}"

    # Build the image
    with console.status(f"Building image {image_name}..."):
        result = os.system(f"cd {driver_path} && docker build -t {image_name} .")

    if result != 0:
        console.print("[red]Failed to build driver image[/red]")
        return

    console.print(f"[green]Successfully built image: {image_name}[/green]")

    # Push if requested
    if push:
        with console.status(f"Pushing image {image_name}..."):
            result = os.system(f"docker push {image_name}")

        if result != 0:
            console.print("[red]Failed to push driver image[/red]")
            return

        console.print(f"[green]Successfully pushed image: {image_name}[/green]")


@driver_app.command("info")
def driver_info(
    driver_name: str = typer.Argument(..., help="Driver name to get info for"),
) -> None:
    """Show detailed information about a driver"""
    driver = config_manager.get_driver(driver_name)
    if not driver:
        console.print(f"[red]Driver '{driver_name}' not found[/red]")
        return

    console.print(f"[bold]Driver: {driver.name}[/bold]")
    console.print(f"Description: {driver.description}")
    console.print(f"Version: {driver.version}")
    console.print(f"Maintainer: {driver.maintainer}")
    console.print(f"Image: {driver.image}")

    if driver.ports:
        console.print("\n[bold]Ports:[/bold]")
        for port in driver.ports:
            console.print(f"  {port}")

    # Get driver path
    driver_path = config_manager.get_driver_path(driver_name)
    if driver_path:
        console.print(f"\n[bold]Path:[/bold] {driver_path}")

        # Check for README
        readme_path = driver_path / "README.md"
        if readme_path.exists():
            console.print("\n[bold]README:[/bold]")
            with open(readme_path, "r") as f:
                console.print(f.read())


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


if __name__ == "__main__":
    app()
