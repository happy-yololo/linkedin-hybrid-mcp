"""Local storage path helpers for auth and session scaffolding."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_DIRNAME = "linkedin-hybrid-mcp"
SESSION_FILENAME = "session.json"


@dataclass(frozen=True)
class StoragePaths:
    """Resolved local filesystem paths used by the auth scaffold."""

    root_dir: Path
    session_file: Path


def resolve_storage_root(
    *,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Resolve the local data directory for persisted auth state."""

    env_map = env if env is not None else os.environ

    explicit_root = env_map.get("LINKEDIN_HYBRID_MCP_HOME")
    if explicit_root:
        return Path(explicit_root).expanduser()

    xdg_data_home = env_map.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / APP_DIRNAME

    home_dir = home if home is not None else Path.home()
    return home_dir.expanduser() / ".local" / "share" / APP_DIRNAME


def resolve_storage_paths(
    *,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> StoragePaths:
    """Return all local storage paths required by the auth scaffold."""

    root_dir = resolve_storage_root(env=env, home=home)
    return StoragePaths(
        root_dir=root_dir,
        session_file=root_dir / SESSION_FILENAME,
    )
