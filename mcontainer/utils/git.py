"""
Git repository handling utilities for MC
"""

import re
from typing import Optional, Tuple


def parse_git_url(url: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a Git URL into its components: hostname, owner, repo

    Supports formats:
    - git@github.com:owner/repo.git
    - https://github.com/owner/repo.git
    - github.com/owner/repo

    Returns:
    Tuple of (hostname, owner, repo) or None if invalid
    """
    # SSH format: git@github.com:owner/repo.git
    ssh_pattern = r"^(?:git@)?([\w\.-]+)(?::)([\w\.-]+)/([\w\.-]+)(?:\.git)?$"

    # HTTPS format: https://github.com/owner/repo.git
    https_pattern = r"^(?:https?://)([\w\.-]+)/(?:([\w\.-]+)/([\w\.-]+))(?:\.git)?$"

    # Simple format: github.com/owner/repo
    simple_pattern = r"^([\w\.-]+)/(?:([\w\.-]+)/([\w\.-]+))(?:\.git)?$"

    for pattern in [ssh_pattern, https_pattern, simple_pattern]:
        match = re.match(pattern, url)
        if match:
            hostname, owner, repo = match.groups()
            return hostname, owner, repo

    return None


def get_normalized_url(url: str) -> Optional[str]:
    """
    Convert various Git URL formats to a normalized form

    Returns:
    Normalized URL (git@hostname:owner/repo.git) or None if invalid
    """
    parsed = parse_git_url(url)
    if not parsed:
        return None

    hostname, owner, repo = parsed
    return f"git@{hostname}:{owner}/{repo}.git"


def get_repository_name(url: str) -> Optional[str]:
    """Get the repository name from a Git URL"""
    parsed = parse_git_url(url)
    if not parsed:
        return None

    _, _, repo = parsed
    return repo.replace(".git", "")
