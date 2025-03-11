import yaml
from pathlib import Path
from typing import Dict, Optional

from .models import Config, Driver

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "mc"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_DRIVERS_DIR = Path.home() / ".config" / "mc" / "drivers"
PROJECT_ROOT = Path(__file__).parent.parent
BUILTIN_DRIVERS_DIR = PROJECT_ROOT / "drivers"

# Default built-in driver configurations
DEFAULT_DRIVERS = {
    "goose": Driver(
        name="goose",
        description="Goose with MCP servers",
        version="1.0.0",
        maintainer="team@monadical.com",
        image="monadical/mc-goose:latest",
        ports=[8000, 22],
    ),
    "aider": Driver(
        name="aider",
        description="Aider coding assistant",
        version="1.0.0",
        maintainer="team@monadical.com",
        image="monadical/mc-aider:latest",
        ports=[22],
    ),
    "claude-code": Driver(
        name="claude-code",
        description="Claude Code environment",
        version="1.0.0",
        maintainer="team@monadical.com",
        image="monadical/mc-claude-code:latest",
        ports=[22],
    ),
}


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self.config_dir = self.config_path.parent
        self.drivers_dir = DEFAULT_DRIVERS_DIR
        self.config = self._load_or_create_config()

    def _load_or_create_config(self) -> Config:
        """Load existing config or create a new one with defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
                
                # Create a new config from scratch, then update with data from file
                config = Config(
                    docker=config_data.get('docker', {}),
                    defaults=config_data.get('defaults', {})
                )
                
                # Add drivers
                if 'drivers' in config_data:
                    for driver_name, driver_data in config_data['drivers'].items():
                        config.drivers[driver_name] = Driver.model_validate(driver_data)
                
                # Add sessions (stored as simple dictionaries)
                if 'sessions' in config_data:
                    config.sessions = config_data['sessions']
                
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
        
        # Load built-in drivers from directories
        builtin_drivers = self.load_builtin_drivers()
        
        # Merge with default drivers, with directory drivers taking precedence
        drivers = {**DEFAULT_DRIVERS, **builtin_drivers}

        config = Config(
            docker={
                "socket": "/var/run/docker.sock",
                "network": "mc-network",
            },
            drivers=drivers,
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
        """Get a driver by name"""
        return self.config.drivers.get(name)

    def list_drivers(self) -> Dict[str, Driver]:
        """List all available drivers"""
        return self.config.drivers

    def add_session(self, session_id: str, session_data: dict) -> None:
        """Add a session to the config"""
        # Store session data as a dictionary in the config
        self.config.sessions[session_id] = session_data
        self.save_config()

    def remove_session(self, session_id: str) -> None:
        """Remove a session from the config"""
        if session_id in self.config.sessions:
            del self.config.sessions[session_id]
            self.save_config()

    def list_sessions(self) -> Dict:
        """List all sessions in the config"""
        return self.config.sessions
        
    def load_driver_from_dir(self, driver_dir: Path) -> Optional[Driver]:
        """Load a driver configuration from a directory"""
        yaml_path = driver_dir / "mai-driver.yaml"  # Keep this name for backward compatibility
        
        if not yaml_path.exists():
            return None
            
        try:
            with open(yaml_path, "r") as f:
                driver_data = yaml.safe_load(f)
                
            # Extract required fields
            if not all(k in driver_data for k in ["name", "description", "version", "maintainer"]):
                print(f"Driver config {yaml_path} missing required fields")
                return None
                
            # Create driver object
            driver = Driver(
                name=driver_data["name"],
                description=driver_data["description"],
                version=driver_data["version"],
                maintainer=driver_data["maintainer"],
                image=f"monadical/mc-{driver_data['name']}:latest",
                ports=driver_data.get("ports", []),
            )
            
            return driver
        except Exception as e:
            print(f"Error loading driver from {yaml_path}: {e}")
            return None
            
    def load_builtin_drivers(self) -> Dict[str, Driver]:
        """Load all built-in drivers from the drivers directory"""
        drivers = {}
        
        if not BUILTIN_DRIVERS_DIR.exists():
            return drivers
            
        for driver_dir in BUILTIN_DRIVERS_DIR.iterdir():
            if driver_dir.is_dir():
                driver = self.load_driver_from_dir(driver_dir)
                if driver:
                    drivers[driver.name] = driver
                    
        return drivers
        
    def get_driver_path(self, driver_name: str) -> Optional[Path]:
        """Get the directory path for a driver"""
        # Check built-in drivers first
        builtin_path = BUILTIN_DRIVERS_DIR / driver_name
        if builtin_path.exists() and builtin_path.is_dir():
            return builtin_path
            
        # Then check user drivers
        user_path = self.drivers_dir / driver_name
        if user_path.exists() and user_path.is_dir():
            return user_path
            
        return None
