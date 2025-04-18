"""
Session storage management for Cubbi Container Tool.
"""

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

DEFAULT_SESSIONS_FILE = Path.home() / ".config" / "cubbi" / "sessions.yaml"


class SessionManager:
    """Manager for container sessions."""

    def __init__(self, sessions_path: Optional[Path] = None):
        """Initialize the session manager.

        Args:
            sessions_path: Optional path to the sessions file.
                           Defaults to ~/.config/cubbi/sessions.yaml.
        """
        self.sessions_path = sessions_path or DEFAULT_SESSIONS_FILE
        self.sessions = self._load_sessions()

    def _load_sessions(self) -> Dict[str, dict]:
        """Load sessions from file or create an empty sessions file if it doesn't exist."""
        if not self.sessions_path.exists():
            # Create directory if it doesn't exist
            self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
            # Create empty sessions file
            with open(self.sessions_path, "w") as f:
                yaml.safe_dump({}, f)
            # Set secure permissions
            os.chmod(self.sessions_path, 0o600)
            return {}

        # Load existing sessions
        with open(self.sessions_path, "r") as f:
            sessions = yaml.safe_load(f) or {}
        return sessions

    def save(self) -> None:
        """Save the sessions to file."""
        with open(self.sessions_path, "w") as f:
            yaml.safe_dump(self.sessions, f)

    def add_session(self, session_id: str, session_data: dict) -> None:
        """Add a session to storage.

        Args:
            session_id: The unique session ID
            session_data: The session data (Session model dump as dict)
        """
        self.sessions[session_id] = session_data
        self.save()

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            The session data or None if not found
        """
        return self.sessions.get(session_id)

    def list_sessions(self) -> Dict[str, dict]:
        """List all sessions.

        Returns:
            Dict of session ID to session data
        """
        return self.sessions

    def remove_session(self, session_id: str) -> None:
        """Remove a session from storage.

        Args:
            session_id: The session ID to remove
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.save()
