"""
Base driver implementation for MAI
"""

from typing import Dict, Optional

from ..models import Driver


class DriverManager:
    """Manager for MAI drivers"""

    @staticmethod
    def get_default_drivers() -> Dict[str, Driver]:
        """Get the default built-in drivers"""
        from ..config import DEFAULT_DRIVERS

        return DEFAULT_DRIVERS

    @staticmethod
    def get_driver_metadata(driver_name: str) -> Optional[Dict]:
        """Get metadata for a specific driver"""
        from ..config import DEFAULT_DRIVERS

        if driver_name in DEFAULT_DRIVERS:
            return DEFAULT_DRIVERS[driver_name].model_dump()

        return None
