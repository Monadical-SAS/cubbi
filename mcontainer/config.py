import yaml
from pathlib import Path
from typing import Dict, Optional

from .models import Config, Driver

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "mc"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_DRIVERS_DIR = Path.home() / ".config" / "mc" / "drivers"
PROJECT_ROOT = Path(__file__).parent.parent
BUILTIN_DRIVERS_DIR = Path(__file__).parent / "drivers"  # mcontainer/drivers

# Dynamically loaded from drivers directory at runtime
DEFAULT_DRIVERS = {}


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self.config_dir = self.config_path.parent
        self.drivers_dir = DEFAULT_DRIVERS_DIR
        self.config = self._load_or_create_config()

        # Always load package drivers on initialization
        # These are separate from the user config
        self.builtin_drivers = self._load_package_drivers()

    def _load_or_create_config(self) -> Config:
        """Load existing config or create a new one with defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}

                # Create a new config from scratch, then update with data from file
                config = Config(
                    docker=config_data.get("docker", {}),
                    defaults=config_data.get("defaults", {}),
                )

                # Add drivers
                if "drivers" in config_data:
                    for driver_name, driver_data in config_data["drivers"].items():
                        config.drivers[driver_name] = Driver.model_validate(driver_data)

                return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()

    def _create_default_config(self) -> Config:
        """Create a default configuration"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.drivers_dir.mkdir(parents=True, exist_ok=True)

        # Initial config without drivers
        config = Config(
            docker={
                "socket": "/var/run/docker.sock",
                "network": "mc-network",
            },
            defaults={
                "driver": "goose",
            },
        )

        self.save_config(config)
        return config

    def save_config(self, config: Optional[Config] = None) -> None:
        """Save the current config to disk"""
        if config:
            self.config = config

        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Use model_dump with mode="json" for proper serialization of enums
        config_dict = self.config.model_dump(mode="json")

        # Write to file
        with open(self.config_path, "w") as f:
            yaml.dump(config_dict, f)

    def get_driver(self, name: str) -> Optional[Driver]:
        """Get a driver by name, checking builtin drivers first, then user-configured ones"""
        # Check builtin drivers first (package drivers take precedence)
        if name in self.builtin_drivers:
            return self.builtin_drivers[name]
        # If not found, check user-configured drivers
        return self.config.drivers.get(name)

    def list_drivers(self) -> Dict[str, Driver]:
        """List all available drivers (both builtin and user-configured)"""
        # Start with user config drivers
        all_drivers = dict(self.config.drivers)

        # Add builtin drivers, overriding any user drivers with the same name
        # This ensures that package-provided drivers always take precedence
        all_drivers.update(self.builtin_drivers)

        return all_drivers

    # Session management has been moved to SessionManager in session.py

    def load_driver_from_dir(self, driver_dir: Path) -> Optional[Driver]:
        """Load a driver configuration from a directory"""
        # Try with mc-driver.yaml first (new format), then mai-driver.yaml (legacy)
        yaml_path = driver_dir / "mc-driver.yaml"
        if not yaml_path.exists():
            yaml_path = driver_dir / "mai-driver.yaml"  # Backward compatibility
            if not yaml_path.exists():
                return None

        try:
            with open(yaml_path, "r") as f:
                driver_data = yaml.safe_load(f)

            # Extract required fields
            if not all(
                k in driver_data
                for k in ["name", "description", "version", "maintainer"]
            ):
                print(f"Driver config {yaml_path} missing required fields")
                return None

            # Use Driver.model_validate to handle all fields from YAML
            # This will map all fields according to the Driver model structure
            try:
                # Ensure image field is set if not in YAML
                if "image" not in driver_data:
                    driver_data["image"] = f"monadical/mc-{driver_data['name']}:latest"

                driver = Driver.model_validate(driver_data)
                return driver
            except Exception as validation_error:
                print(
                    f"Error validating driver data from {yaml_path}: {validation_error}"
                )
                return None

        except Exception as e:
            print(f"Error loading driver from {yaml_path}: {e}")
            return None

    def _load_package_drivers(self) -> Dict[str, Driver]:
        """Load all package drivers from the mcontainer/drivers directory"""
        drivers = {}

        if not BUILTIN_DRIVERS_DIR.exists():
            return drivers

        # Search for mc-driver.yaml files in each subdirectory
        for driver_dir in BUILTIN_DRIVERS_DIR.iterdir():
            if driver_dir.is_dir():
                driver = self.load_driver_from_dir(driver_dir)
                if driver:
                    drivers[driver.name] = driver

        return drivers

    def get_driver_path(self, driver_name: str) -> Optional[Path]:
        """Get the directory path for a driver"""
        # Check package drivers first (these are the bundled ones)
        package_path = BUILTIN_DRIVERS_DIR / driver_name
        if package_path.exists() and package_path.is_dir():
            return package_path

        # Then check user drivers
        user_path = self.drivers_dir / driver_name
        if user_path.exists() and user_path.is_dir():
            return user_path

        return None
