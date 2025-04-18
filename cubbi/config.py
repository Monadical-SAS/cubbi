from pathlib import Path
from typing import Dict, Optional

import yaml

from .models import Config, Image

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "cubbi"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_IMAGES_DIR = Path.home() / ".config" / "cubbi" / "images"
PROJECT_ROOT = Path(__file__).parent.parent
BUILTIN_IMAGES_DIR = Path(__file__).parent / "images"

# Dynamically loaded from images directory at runtime
DEFAULT_IMAGES = {}


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self.config_dir = self.config_path.parent
        self.images_dir = DEFAULT_IMAGES_DIR
        self.config = self._load_or_create_config()

        # Always load package images on initialization
        # These are separate from the user config
        self.builtin_images = self._load_package_images()

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

                # Add images
                if "images" in config_data:
                    for image_name, image_data in config_data["images"].items():
                        config.images[image_name] = Image.model_validate(image_data)

                return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()

    def _create_default_config(self) -> Config:
        """Create a default configuration"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Initial config without images
        config = Config(
            docker={
                "socket": "/var/run/docker.sock",
                "network": "cubbi-network",
            },
            defaults={
                "image": "goose",
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

    def get_image(self, name: str) -> Optional[Image]:
        """Get an image by name, checking builtin images first, then user-configured ones"""
        # Check builtin images first (package images take precedence)
        if name in self.builtin_images:
            return self.builtin_images[name]
        # If not found, check user-configured images
        return self.config.images.get(name)

    def list_images(self) -> Dict[str, Image]:
        """List all available images (both builtin and user-configured)"""
        # Start with user config images
        all_images = dict(self.config.images)

        # Add builtin images, overriding any user images with the same name
        # This ensures that package-provided images always take precedence
        all_images.update(self.builtin_images)

        return all_images

    # Session management has been moved to SessionManager in session.py

    def load_image_from_dir(self, image_dir: Path) -> Optional[Image]:
        """Load an image configuration from a directory"""
        # Check for image config file
        yaml_path = image_dir / "cubbi-image.yaml"
        if not yaml_path.exists():
            return None

        try:
            with open(yaml_path, "r") as f:
                image_data = yaml.safe_load(f)

            # Extract required fields
            if not all(
                k in image_data
                for k in ["name", "description", "version", "maintainer"]
            ):
                print(f"Image config {yaml_path} missing required fields")
                return None

            # Use Image.model_validate to handle all fields from YAML
            # This will map all fields according to the Image model structure
            try:
                # Ensure image field is set if not in YAML
                if "image" not in image_data:
                    image_data["image"] = f"monadical/cubbi-{image_data['name']}:latest"

                image = Image.model_validate(image_data)
                return image
            except Exception as validation_error:
                print(
                    f"Error validating image data from {yaml_path}: {validation_error}"
                )
                return None

        except Exception as e:
            print(f"Error loading image from {yaml_path}: {e}")
            return None

    def _load_package_images(self) -> Dict[str, Image]:
        """Load all package images from the cubbi/images directory"""
        images = {}

        if not BUILTIN_IMAGES_DIR.exists():
            return images

        # Search for cubbi-image.yaml files in each subdirectory
        for image_dir in BUILTIN_IMAGES_DIR.iterdir():
            if image_dir.is_dir():
                image = self.load_image_from_dir(image_dir)
                if image:
                    images[image.name] = image

        return images

    def get_image_path(self, image_name: str) -> Optional[Path]:
        """Get the directory path for an image"""
        # Check package images first (these are the bundled ones)
        package_path = BUILTIN_IMAGES_DIR / image_name
        if package_path.exists() and package_path.is_dir():
            return package_path

        # Then check user images
        user_path = self.images_dir / image_name
        if user_path.exists() and user_path.is_dir():
            return user_path

        return None
