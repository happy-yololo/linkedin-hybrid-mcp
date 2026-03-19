from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from linkedin_hybrid_mcp.auth import (
    AuthFlowNotImplementedError,
    SessionMetadata,
    auth_status,
    browser_bootstrap_placeholder,
    clear_session,
    default_session_metadata,
    load_session,
    refresh_session_placeholder,
    save_session,
)
from linkedin_hybrid_mcp.config import resolve_storage_paths, resolve_storage_root


def test_resolve_storage_root_prefers_explicit_home(tmp_path: Path) -> None:
    root = resolve_storage_root(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    assert root == tmp_path / "state"


def test_resolve_storage_root_falls_back_to_xdg_data_home(tmp_path: Path) -> None:
    root = resolve_storage_root(env={"XDG_DATA_HOME": str(tmp_path / "xdg")})

    assert root == tmp_path / "xdg" / "linkedin-hybrid-mcp"


def test_resolve_storage_paths_use_default_session_filename(tmp_path: Path) -> None:
    paths = resolve_storage_paths(home=tmp_path, env={})

    assert paths.root_dir == tmp_path / ".local" / "share" / "linkedin-hybrid-mcp"
    assert paths.session_file == paths.root_dir / "session.json"


def test_load_session_returns_default_scaffold_when_missing(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    session = load_session(paths)

    assert session.login_state == "empty"
    assert session.cookies_present is False
    assert "No LinkedIn authentication is implemented yet." in session.notes


def test_save_then_load_session_round_trips_json(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    expires_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
    session = SessionMetadata(
        account_identifier="user@example.com",
        source="browser_bootstrap",
        login_state="bootstrapped",
        expires_at=expires_at,
        cookies_present=True,
        headers_present=True,
        browser_profile_path="/tmp/browser-profile",
        notes=["session captured locally"],
    )

    save_session(session, paths)
    loaded = load_session(paths)

    assert loaded.account_identifier == "user@example.com"
    assert loaded.source == "browser_bootstrap"
    assert loaded.login_state == "bootstrapped"
    assert loaded.expires_at == expires_at
    assert loaded.cookies_present is True
    assert loaded.headers_present is True
    assert loaded.browser_profile_path == "/tmp/browser-profile"
    assert loaded.notes == ["session captured locally"]


def test_clear_session_removes_persisted_file(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    save_session(default_session_metadata(), paths)
    clear_session(paths)

    assert paths.session_file.exists() is False


def test_auth_status_reports_missing_when_no_file_exists(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    status = auth_status(paths=paths)

    assert status.state == "missing"
    assert status.is_authenticated is False
    assert status.can_attempt_http is False
    assert status.has_persisted_session is False


def test_auth_status_reports_expired_for_stale_session(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    session = SessionMetadata(
        login_state="bootstrapped",
        expires_at=now - timedelta(minutes=1),
        cookies_present=True,
    )
    save_session(session, paths)

    status = auth_status(paths=paths, now=now)

    assert status.state == "expired"
    assert status.is_authenticated is False
    assert status.has_persisted_session is True


def test_auth_status_reports_incomplete_without_cookies(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    session = SessionMetadata(
        login_state="bootstrapped",
        cookies_present=False,
    )
    save_session(session, paths)

    status = auth_status(paths=paths)

    assert status.state == "incomplete"
    assert status.is_authenticated is False
    assert status.can_attempt_http is False


def test_auth_status_reports_ready_with_unexpired_cookies(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    session = SessionMetadata(
        login_state="bootstrapped",
        expires_at=now + timedelta(hours=1),
        cookies_present=True,
        headers_present=True,
    )
    save_session(session, paths)

    status = auth_status(paths=paths, now=now)

    assert status.state == "ready"
    assert status.is_authenticated is True
    assert status.can_attempt_http is True
    assert status.has_persisted_session is True


def test_browser_bootstrap_placeholder_is_explicit(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    with pytest.raises(AuthFlowNotImplementedError, match="Browser bootstrap is not implemented"):
        browser_bootstrap_placeholder(paths)


def test_refresh_placeholder_is_explicit(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    with pytest.raises(AuthFlowNotImplementedError, match="Session refresh is not implemented"):
        refresh_session_placeholder(default_session_metadata(), paths)
