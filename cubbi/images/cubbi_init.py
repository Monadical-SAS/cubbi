#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["ruamel.yaml"]
# ///
"""
Standalone Cubbi initialization script

This is a self-contained script that includes all the necessary initialization
logic without requiring the full cubbi package to be installed.
"""

import grp
import importlib.util
import os
import pwd
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from ruamel.yaml import YAML


# Status Management
class StatusManager:
    """Manages initialization status and logging"""

    def __init__(
        self, log_file: str = "/cubbi/init.log", status_file: str = "/cubbi/init.status"
    ):
        self.log_file = Path(log_file)
        self.status_file = Path(status_file)
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging to both stdout and log file"""
        self.log_file.touch(exist_ok=True)
        self.set_status(False)

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message with timestamp"""
        print(message)
        sys.stdout.flush()

        with open(self.log_file, "a") as f:
            f.write(message + "\n")
            f.flush()

    def set_status(self, complete: bool) -> None:
        """Set initialization completion status"""
        status = "true" if complete else "false"
        with open(self.status_file, "w") as f:
            f.write(f"INIT_COMPLETE={status}\n")

    def start_initialization(self) -> None:
        """Mark initialization as started"""
        self.set_status(False)

    def complete_initialization(self) -> None:
        """Mark initialization as completed"""
        self.set_status(True)


# Configuration Management
@dataclass
class PersistentConfig:
    """Persistent configuration mapping"""

    source: str
    target: str
    type: str = "directory"
    description: str = ""


@dataclass
class ImageConfig:
    """Cubbi image configuration"""

    name: str
    description: str
    version: str
    maintainer: str
    image: str
    persistent_configs: List[PersistentConfig] = field(default_factory=list)


class ConfigParser:
    """Parses Cubbi image configuration and environment variables"""

    def __init__(self, config_file: str = "/cubbi/cubbi_image.yaml"):
        self.config_file = Path(config_file)
        self.environment: Dict[str, str] = dict(os.environ)

    def load_image_config(self) -> ImageConfig:
        """Load and parse the cubbi_image.yaml configuration"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        yaml = YAML(typ="safe")
        with open(self.config_file, "r") as f:
            config_data = yaml.load(f)

        # Parse persistent configurations
        persistent_configs = []
        for pc_data in config_data.get("persistent_configs", []):
            persistent_configs.append(PersistentConfig(**pc_data))

        return ImageConfig(
            name=config_data["name"],
            description=config_data["description"],
            version=config_data["version"],
            maintainer=config_data["maintainer"],
            image=config_data["image"],
            persistent_configs=persistent_configs,
        )

    def get_cubbi_config(self) -> Dict[str, Any]:
        """Get standard Cubbi configuration from environment"""
        return {
            "user_id": int(self.environment.get("CUBBI_USER_ID", "1000")),
            "group_id": int(self.environment.get("CUBBI_GROUP_ID", "1000")),
            "run_command": self.environment.get("CUBBI_RUN_COMMAND"),
            "no_shell": self.environment.get("CUBBI_NO_SHELL", "false").lower()
            == "true",
            "config_dir": self.environment.get("CUBBI_CONFIG_DIR", "/cubbi-config"),
            "persistent_links": self.environment.get("CUBBI_PERSISTENT_LINKS", ""),
        }

    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP server configuration from environment"""
        mcp_count = int(self.environment.get("MCP_COUNT", "0"))
        mcp_servers = []

        for idx in range(mcp_count):
            server = {
                "name": self.environment.get(f"MCP_{idx}_NAME"),
                "type": self.environment.get(f"MCP_{idx}_TYPE"),
                "host": self.environment.get(f"MCP_{idx}_HOST"),
                "url": self.environment.get(f"MCP_{idx}_URL"),
            }
            if server["name"]:  # Only add if name is present
                mcp_servers.append(server)

        return {"count": mcp_count, "servers": mcp_servers}


# Core Management Classes
class UserManager:
    """Manages user and group creation/modification in containers"""

    def __init__(self, status: StatusManager):
        self.status = status
        self.username = "cubbi"

    def _run_command(self, cmd: list[str]) -> bool:
        """Run a system command and log the result"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stdout:
                self.status.log(f"Command output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            self.status.log(f"Command failed: {' '.join(cmd)}", "ERROR")
            self.status.log(f"Error: {e.stderr}", "ERROR")
            return False

    def setup_user_and_group(self, user_id: int, group_id: int) -> bool:
        """Set up user and group with specified IDs"""
        self.status.log(
            f"Setting up user '{self.username}' with UID: {user_id}, GID: {group_id}"
        )

        # Handle group creation/modification
        try:
            existing_group = grp.getgrnam(self.username)
            if existing_group.gr_gid != group_id:
                self.status.log(
                    f"Modifying group '{self.username}' GID from {existing_group.gr_gid} to {group_id}"
                )
                if not self._run_command(
                    ["groupmod", "-g", str(group_id), self.username]
                ):
                    return False
        except KeyError:
            if not self._run_command(["groupadd", "-g", str(group_id), self.username]):
                return False

        # Handle user creation/modification
        try:
            existing_user = pwd.getpwnam(self.username)
            if existing_user.pw_uid != user_id or existing_user.pw_gid != group_id:
                self.status.log(
                    f"Modifying user '{self.username}' UID from {existing_user.pw_uid} to {user_id}, GID from {existing_user.pw_gid} to {group_id}"
                )
                if not self._run_command(
                    [
                        "usermod",
                        "--uid",
                        str(user_id),
                        "--gid",
                        str(group_id),
                        self.username,
                    ]
                ):
                    return False
        except KeyError:
            if not self._run_command(
                [
                    "useradd",
                    "--shell",
                    "/bin/bash",
                    "--uid",
                    str(user_id),
                    "--gid",
                    str(group_id),
                    "--no-create-home",
                    self.username,
                ]
            ):
                return False

        return True


class DirectoryManager:
    """Manages directory creation and permission setup"""

    def __init__(self, status: StatusManager):
        self.status = status

    def create_directory(
        self, path: str, user_id: int, group_id: int, mode: int = 0o755
    ) -> bool:
        """Create a directory with proper ownership and permissions"""
        dir_path = Path(path)

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            os.chown(path, user_id, group_id)
            dir_path.chmod(mode)
            self.status.log(f"Created directory: {path}")
            return True
        except Exception as e:
            self.status.log(
                f"Failed to create/configure directory {path}: {e}", "ERROR"
            )
            return False

    def setup_standard_directories(self, user_id: int, group_id: int) -> bool:
        """Set up standard Cubbi directories"""
        directories = [
            ("/app", 0o755),
            ("/cubbi-config", 0o755),
            ("/cubbi-config/home", 0o755),
        ]

        self.status.log("Setting up standard directories")

        success = True
        for dir_path, mode in directories:
            if not self.create_directory(dir_path, user_id, group_id, mode):
                success = False

        # Create /home/cubbi as a symlink to /cubbi-config/home
        try:
            home_cubbi = Path("/home/cubbi")
            if home_cubbi.exists() or home_cubbi.is_symlink():
                home_cubbi.unlink()

            self.status.log("Creating /home/cubbi as symlink to /cubbi-config/home")
            home_cubbi.symlink_to("/cubbi-config/home")
            os.lchown("/home/cubbi", user_id, group_id)
        except Exception as e:
            self.status.log(f"Failed to create home directory symlink: {e}", "ERROR")
            success = False

        # Create .local directory in the persistent home
        local_dir = Path("/cubbi-config/home/.local")
        if not self.create_directory(str(local_dir), user_id, group_id, 0o755):
            success = False

        # Copy /root/.local/bin to user's home if it exists
        root_local_bin = Path("/root/.local/bin")
        if root_local_bin.exists():
            user_local_bin = Path("/cubbi-config/home/.local/bin")
            try:
                user_local_bin.mkdir(parents=True, exist_ok=True)

                for item in root_local_bin.iterdir():
                    if item.is_file():
                        shutil.copy2(item, user_local_bin / item.name)
                    elif item.is_dir():
                        shutil.copytree(
                            item, user_local_bin / item.name, dirs_exist_ok=True
                        )

                self._chown_recursive(user_local_bin, user_id, group_id)
                self.status.log("Copied /root/.local/bin to user directory")

            except Exception as e:
                self.status.log(f"Failed to copy /root/.local/bin: {e}", "ERROR")
                success = False

        return success

    def _chown_recursive(self, path: Path, user_id: int, group_id: int) -> None:
        """Recursively change ownership of a directory"""
        try:
            os.chown(path, user_id, group_id)
            for item in path.iterdir():
                if item.is_dir():
                    self._chown_recursive(item, user_id, group_id)
                else:
                    os.chown(item, user_id, group_id)
        except Exception as e:
            self.status.log(
                f"Warning: Could not change ownership of {path}: {e}", "WARNING"
            )


class ConfigManager:
    """Manages persistent configuration symlinks and mappings"""

    def __init__(self, status: StatusManager):
        self.status = status

    def create_symlink(
        self, source_path: str, target_path: str, user_id: int, group_id: int
    ) -> bool:
        """Create a symlink with proper ownership"""
        try:
            source = Path(source_path)

            parent_dir = source.parent
            if not parent_dir.exists():
                self.status.log(f"Creating parent directory: {parent_dir}")
                parent_dir.mkdir(parents=True, exist_ok=True)
                os.chown(parent_dir, user_id, group_id)

            self.status.log(f"Creating symlink: {source_path} -> {target_path}")
            if source.is_symlink() or source.exists():
                source.unlink()

            source.symlink_to(target_path)
            os.lchown(source_path, user_id, group_id)

            return True
        except Exception as e:
            self.status.log(
                f"Failed to create symlink {source_path} -> {target_path}: {e}", "ERROR"
            )
            return False

    def _ensure_target_directory(
        self, target_path: str, user_id: int, group_id: int
    ) -> bool:
        """Ensure the target directory exists with proper ownership"""
        try:
            target_dir = Path(target_path)
            if not target_dir.exists():
                self.status.log(f"Creating target directory: {target_path}")
                target_dir.mkdir(parents=True, exist_ok=True)

            # Set ownership of the target directory to cubbi user
            os.chown(target_path, user_id, group_id)
            self.status.log(f"Set ownership of {target_path} to {user_id}:{group_id}")
            return True
        except Exception as e:
            self.status.log(
                f"Failed to ensure target directory {target_path}: {e}", "ERROR"
            )
            return False

    def setup_persistent_configs(
        self, persistent_configs: List[PersistentConfig], user_id: int, group_id: int
    ) -> bool:
        """Set up persistent configuration symlinks from image config"""
        if not persistent_configs:
            self.status.log("No persistent configurations defined in image config")
            return True

        success = True
        for config in persistent_configs:
            # Ensure target directory exists with proper ownership
            if not self._ensure_target_directory(config.target, user_id, group_id):
                success = False
                continue

            if not self.create_symlink(config.source, config.target, user_id, group_id):
                success = False

        return success


class CommandManager:
    """Manages command execution and user switching"""

    def __init__(self, status: StatusManager):
        self.status = status
        self.username = "cubbi"

    def run_as_user(self, command: List[str], user: str = None) -> int:
        """Run a command as the specified user using gosu"""
        if user is None:
            user = self.username

        full_command = ["gosu", user] + command
        self.status.log(f"Executing as {user}: {' '.join(command)}")

        try:
            result = subprocess.run(full_command, check=False)
            return result.returncode
        except Exception as e:
            self.status.log(f"Failed to execute command: {e}", "ERROR")
            return 1

    def run_user_command(self, command: str) -> int:
        """Run user-specified command as cubbi user"""
        if not command:
            return 0

        self.status.log(f"Executing user command: {command}")
        return self.run_as_user(["sh", "-c", command])

    def exec_as_user(self, args: List[str]) -> None:
        """Execute the final command as cubbi user (replaces current process)"""
        if not args:
            args = ["tail", "-f", "/dev/null"]

        self.status.log(
            f"Switching to user '{self.username}' and executing: {' '.join(args)}"
        )

        try:
            os.execvp("gosu", ["gosu", self.username] + args)
        except Exception as e:
            self.status.log(f"Failed to exec as user: {e}", "ERROR")
            sys.exit(1)


# Tool Plugin System
class ToolPlugin(ABC):
    """Base class for tool-specific initialization plugins"""

    def __init__(self, status: StatusManager, config: Dict[str, Any]):
        self.status = status
        self.config = config

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return the name of the tool this plugin supports"""
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """Main tool initialization logic"""
        pass

    def integrate_mcp_servers(self, mcp_config: Dict[str, Any]) -> bool:
        """Integrate with available MCP servers"""
        return True


# Main Initializer
class CubbiInitializer:
    """Main Cubbi initialization orchestrator"""

    def __init__(self):
        self.status = StatusManager()
        self.config_parser = ConfigParser()
        self.user_manager = UserManager(self.status)
        self.directory_manager = DirectoryManager(self.status)
        self.config_manager = ConfigManager(self.status)
        self.command_manager = CommandManager(self.status)

    def run_initialization(self, final_args: List[str]) -> None:
        """Run the complete initialization process"""
        try:
            self.status.start_initialization()

            # Load configuration
            image_config = self.config_parser.load_image_config()
            cubbi_config = self.config_parser.get_cubbi_config()
            mcp_config = self.config_parser.get_mcp_config()

            self.status.log(f"Initializing {image_config.name} v{image_config.version}")

            # Core initialization
            success = self._run_core_initialization(image_config, cubbi_config)
            if not success:
                self.status.log("Core initialization failed", "ERROR")
                sys.exit(1)

            # Tool-specific initialization
            success = self._run_tool_initialization(
                image_config, cubbi_config, mcp_config
            )
            if not success:
                self.status.log("Tool initialization failed", "ERROR")
                sys.exit(1)

            # Mark complete
            self.status.complete_initialization()

            # Handle commands
            self._handle_command_execution(cubbi_config, final_args)

        except Exception as e:
            self.status.log(f"Initialization failed with error: {e}", "ERROR")
            sys.exit(1)

    def _run_core_initialization(self, image_config, cubbi_config) -> bool:
        """Run core Cubbi initialization steps"""
        user_id = cubbi_config["user_id"]
        group_id = cubbi_config["group_id"]

        if not self.user_manager.setup_user_and_group(user_id, group_id):
            return False

        if not self.directory_manager.setup_standard_directories(user_id, group_id):
            return False

        config_path = Path(cubbi_config["config_dir"])
        if not config_path.exists():
            self.status.log(f"Creating config directory: {cubbi_config['config_dir']}")
            try:
                config_path.mkdir(parents=True, exist_ok=True)
                os.chown(cubbi_config["config_dir"], user_id, group_id)
            except Exception as e:
                self.status.log(f"Failed to create config directory: {e}", "ERROR")
                return False

        if not self.config_manager.setup_persistent_configs(
            image_config.persistent_configs, user_id, group_id
        ):
            return False

        return True

    def _run_tool_initialization(self, image_config, cubbi_config, mcp_config) -> bool:
        """Run tool-specific initialization"""
        # Look for a tool-specific plugin file in the same directory
        plugin_name = image_config.name.lower().replace("-", "_")
        plugin_file = Path(__file__).parent / f"{plugin_name}_plugin.py"

        if not plugin_file.exists():
            self.status.log(
                f"No tool-specific plugin found at {plugin_file}, skipping tool initialization"
            )
            return True

        try:
            # Dynamically load the plugin module
            spec = importlib.util.spec_from_file_location(
                f"{image_config.name.lower()}_plugin", plugin_file
            )
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)

            # Find the plugin class (should inherit from ToolPlugin)
            plugin_class = None
            for attr_name in dir(plugin_module):
                attr = getattr(plugin_module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "tool_name")
                    and hasattr(attr, "initialize")
                    and attr_name != "ToolPlugin"
                ):  # Skip the base class
                    plugin_class = attr
                    break

            if not plugin_class:
                self.status.log(
                    f"No valid plugin class found in {plugin_file}", "ERROR"
                )
                return False

            # Instantiate and run the plugin
            plugin = plugin_class(
                self.status,
                {
                    "image_config": image_config,
                    "cubbi_config": cubbi_config,
                    "mcp_config": mcp_config,
                },
            )

            self.status.log(f"Running {plugin.tool_name}-specific initialization")

            if not plugin.initialize():
                self.status.log(f"{plugin.tool_name} initialization failed", "ERROR")
                return False

            if not plugin.integrate_mcp_servers(mcp_config):
                self.status.log(f"{plugin.tool_name} MCP integration failed", "ERROR")
                return False

            return True

        except Exception as e:
            self.status.log(
                f"Failed to load or execute plugin {plugin_file}: {e}", "ERROR"
            )
            return False

    def _handle_command_execution(self, cubbi_config, final_args):
        """Handle command execution"""
        exit_code = 0

        if cubbi_config["run_command"]:
            self.status.log("--- Executing initial command ---")
            exit_code = self.command_manager.run_user_command(
                cubbi_config["run_command"]
            )
            self.status.log(
                f"--- Initial command finished (exit code: {exit_code}) ---"
            )

            if cubbi_config["no_shell"]:
                self.status.log(
                    "--- CUBBI_NO_SHELL=true, exiting container without starting shell ---"
                )
                sys.exit(exit_code)

        self.command_manager.exec_as_user(final_args)


def main() -> int:
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cubbi container initialization script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script initializes a Cubbi container environment by:
1. Setting up user and group with proper IDs
2. Creating standard directories with correct permissions
3. Setting up persistent configuration symlinks
4. Running tool-specific initialization if available
5. Executing user commands or starting an interactive shell

Environment Variables:
  CUBBI_USER_ID      User ID for the cubbi user (default: 1000)
  CUBBI_GROUP_ID     Group ID for the cubbi user (default: 1000)
  CUBBI_RUN_COMMAND  Initial command to run before shell
  CUBBI_NO_SHELL     Exit after run command instead of starting shell
  CUBBI_CONFIG_DIR   Configuration directory path (default: /cubbi-config)
  MCP_COUNT          Number of MCP servers to configure
  MCP_<N>_NAME       Name of MCP server N
  MCP_<N>_TYPE       Type of MCP server N
  MCP_<N>_HOST       Host of MCP server N
  MCP_<N>_URL        URL of MCP server N

Examples:
  cubbi_init.py                    # Initialize and start bash shell
  cubbi_init.py --help             # Show this help message
  cubbi_init.py /bin/zsh           # Initialize and start zsh shell
  cubbi_init.py python script.py   # Initialize and run python script
        """,
    )

    parser.add_argument(
        "command",
        nargs="*",
        help="Command to execute after initialization (default: interactive shell)",
    )

    # Parse known args to handle cases where the command might have its own arguments
    args, unknown = parser.parse_known_args()

    # Combine parsed command with unknown args
    final_args = args.command + unknown

    # Handle the common case where docker CMD passes ["tail", "-f", "/dev/null"]
    # This should be treated as "no specific command" (empty args)
    if final_args == ["tail", "-f", "/dev/null"]:
        final_args = []

    initializer = CubbiInitializer()
    initializer.run_initialization(final_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
