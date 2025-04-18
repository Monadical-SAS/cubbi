"""
Base image implementation for MAI
"""

from typing import Dict, Optional

from ..models import Image


class ImageManager:
    """Manager for MAI images"""

    @staticmethod
    def get_default_images() -> Dict[str, Image]:
        """Get the default built-in images"""
        from ..config import DEFAULT_IMAGES

        return DEFAULT_IMAGES

    @staticmethod
    def get_image_metadata(image_name: str) -> Optional[Dict]:
        """Get metadata for a specific image"""
        from ..config import DEFAULT_IMAGES

        if image_name in DEFAULT_IMAGES:
            return DEFAULT_IMAGES[image_name].model_dump()

        return None
