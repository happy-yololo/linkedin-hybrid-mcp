"""Minimal MCP server skeleton for current milestone."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    FastMCP = None  # type: ignore[assignment]

from linkedin_hybrid_mcp import __version__
from linkedin_hybrid_mcp.auth import (
    AuthFlowNotImplementedError,
    auth_status,
    browser_bootstrap_placeholder,
    clear_session,
    default_session_metadata,
    refresh_session_placeholder,
)
from linkedin_hybrid_mcp.client import transport_self_test
from linkedin_hybrid_mcp.config import StoragePaths

SERVICE_NAME = "linkedin-hybrid-mcp"
MILESTONE = "milestone-4"


class _UnavailableMCP:
    """Small stand-in so the module stays importable without optional deps."""

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator

    def run(self) -> None:
        raise RuntimeError(
            "The 'mcp' package is required to run the server. Install dependencies first."
        )


mcp = FastMCP(SERVICE_NAME) if FastMCP is not None else _UnavailableMCP()


def health_payload() -> dict[str, str]:
    """Return a stable liveness payload for basic smoke tests."""

    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": __version__,
    }


def service_info_payload() -> dict[str, object]:
    """Return current milestone and architecture metadata."""

    current_auth_status = auth_status().to_dict()
    current_transport_status = transport_self_test().to_dict()

    return {
        "service": SERVICE_NAME,
        "version": __version__,
        "milestone": MILESTONE,
        "architecture": {
            "mode": "api-first",
            "browser_usage": "auth bootstrap and fallback only",
            "implemented": "partial",
        },
        "auth": {
            "implemented": "local session scaffold only",
            "status": current_auth_status,
        },
        "transport": {
            "implemented": "generic authenticated request scaffold only",
            "status": current_transport_status,
        },
        "notes": [
            "Milestone 4 adds safe diagnostics payloads and MCP tool wrappers for local auth and transport visibility.",
            "LinkedIn auth, browser bootstrap, refresh flows, and LinkedIn-specific API integrations are still not implemented.",
        ],
    }


def auth_status_payload(*, paths: StoragePaths | None = None) -> dict[str, object]:
    """Return a safe snapshot of current auth/session readiness."""

    status = auth_status(paths=paths)
    return {
        "service": SERVICE_NAME,
        "milestone": MILESTONE,
        "auth": status.to_dict(),
        "notes": [
            "This tool reports local session metadata readiness only.",
            "It does not perform LinkedIn login or validate a live remote session.",
        ],
    }


def transport_diagnostics_payload(*, paths: StoragePaths | None = None) -> dict[str, object]:
    """Return non-network transport readiness diagnostics."""

    diagnostics = transport_self_test(paths=paths)
    return {
        "service": SERVICE_NAME,
        "milestone": MILESTONE,
        "transport": diagnostics.to_dict(),
        "runtime": {
            "python_version": ".".join(str(part) for part in sys.version_info[:3]),
            "mcp_dependency_available": FastMCP is not None,
            "tool_wrapper_mode": "fastmcp" if FastMCP is not None else "import-only",
        },
        "notes": [
            "This tool does not make live network calls.",
            "The module stays importable even when the optional MCP runtime dependency is unavailable.",
        ],
    }


def clear_session_payload(*, paths: StoragePaths | None = None) -> dict[str, object]:
    """Delete persisted session metadata and report the result safely."""

    status_before = auth_status(paths=paths)
    clear_session(paths=paths)
    status_after = auth_status(paths=paths)
    return {
        "service": SERVICE_NAME,
        "milestone": MILESTONE,
        "cleared": True,
        "session_path": str(status_after.session_path),
        "auth_before": status_before.to_dict(),
        "auth_after": status_after.to_dict(),
        "notes": [
            "Only local session metadata is removed.",
            "No remote logout or LinkedIn account action is performed.",
        ],
    }


def auth_flow_placeholders_payload(*, paths: StoragePaths | None = None) -> dict[str, object]:
    """Expose bootstrap and refresh placeholders without claiming implementation."""

    bootstrap_message = ""
    refresh_message = ""

    try:
        browser_bootstrap_placeholder(paths=paths)
    except AuthFlowNotImplementedError as exc:
        bootstrap_message = str(exc)

    try:
        refresh_session_placeholder(default_session_metadata(), paths=paths)
    except AuthFlowNotImplementedError as exc:
        refresh_message = str(exc)

    return {
        "service": SERVICE_NAME,
        "milestone": MILESTONE,
        "bootstrap": {
            "implemented": False,
            "status": "not_implemented",
            "message": bootstrap_message,
        },
        "refresh": {
            "implemented": False,
            "status": "not_implemented",
            "message": refresh_message,
        },
        "notes": [
            "These flows are intentionally placeholders.",
            "The payload surfaces future entry points without attempting login or refresh behavior.",
        ],
    }


def service_diagnostics_payload(*, paths: StoragePaths | None = None) -> dict[str, object]:
    """Return the combined safe diagnostics surface for the current scaffold."""

    return {
        "service": SERVICE_NAME,
        "version": __version__,
        "milestone": MILESTONE,
        "auth_status": auth_status_payload(paths=paths),
        "transport_self_test": transport_diagnostics_payload(paths=paths),
        "auth_placeholders": auth_flow_placeholders_payload(paths=paths),
    }


@mcp.tool()
def health() -> dict[str, str]:
    """Report basic service liveness metadata."""

    return health_payload()


@mcp.tool()
def service_info() -> dict[str, object]:
    """Describe the current scaffold and intended architecture."""

    return service_info_payload()


@mcp.tool()
def auth_status_tool() -> dict[str, object]:
    """Report local auth/session readiness without network access."""

    return auth_status_payload()


@mcp.tool()
def transport_self_test_tool() -> dict[str, object]:
    """Return non-network transport diagnostics for the current scaffold."""

    return transport_diagnostics_payload()


@mcp.tool()
def clear_session_tool() -> dict[str, object]:
    """Remove the local session scaffold and report the before/after state."""

    return clear_session_payload()


@mcp.tool()
def auth_flow_placeholders() -> dict[str, object]:
    """Describe unimplemented bootstrap and refresh entry points."""

    return auth_flow_placeholders_payload()


@mcp.tool()
def service_diagnostics() -> dict[str, object]:
    """Return a combined safe diagnostics snapshot for the current scaffold."""

    return service_diagnostics_payload()
