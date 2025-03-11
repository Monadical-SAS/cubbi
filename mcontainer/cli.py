import os
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigManager
from .container import ContainerManager
from .models import SessionStatus

app = typer.Typer(help="Monadical Container Tool")
session_app = typer.Typer(help="Manage MC sessions")
driver_app = typer.Typer(help="Manage MC drivers", no_args_is_help=True)
app.add_typer(session_app, name="session", no_args_is_help=True)
app.add_typer(driver_app, name="driver", no_args_is_help=True)

console = Console()
config_manager = ConfigManager()
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

        table.add_row(
            session.id,
            session.name,
            session.driver,
            f"[{status_color}]{session.status}[/{status_color}]",
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
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Session name"),
    no_connect: bool = typer.Option(
        False, "--no-connect", help="Don't automatically connect to the session"
    ),
    no_mount: bool = typer.Option(
        False, "--no-mount", help="Don't mount local directory to /app"
    ),
) -> None:
    """Create a new MC session"""
    # Use default driver if not specified
    if not driver:
        driver = config_manager.config.defaults.get("driver", "goose")

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

    with console.status(f"Creating session with driver '{driver}'..."):
        session = container_manager.create_session(
            driver_name=driver,
            project=project,
            environment=environment,
            session_name=name,
            mount_local=not no_mount,
        )

    if session:
        console.print("[green]Session created successfully![/green]")
        console.print(f"Session ID: {session.id}")
        console.print(f"Driver: {session.driver}")

        if session.ports:
            console.print("Ports:")
            for container_port, host_port in session.ports.items():
                console.print(f"  {container_port} -> {host_port}")

        # Auto-connect unless --no-connect flag is provided
        if not no_connect:
            console.print(f"\nConnecting to session {session.id}...")
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
) -> None:
    """Stream logs from a MC session"""
    if follow:
        console.print(f"Streaming logs from session {session_id}... (Ctrl+C to exit)")
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
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Session name"),
    no_connect: bool = typer.Option(
        False, "--no-connect", help="Don't automatically connect to the session"
    ),
    no_mount: bool = typer.Option(
        False, "--no-mount", help="Don't mount local directory to /app"
    ),
) -> None:
    """Create a new MC session with a project repository"""
    create_session(
        driver=driver,
        project=project,
        env=env,
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


if __name__ == "__main__":
    app()
