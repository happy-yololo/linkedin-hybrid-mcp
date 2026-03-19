"""Minimal MCP server skeleton for milestone 1."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    FastMCP = None  # type: ignore[assignment]

from linkedin_hybrid_mcp import __version__
from linkedin_hybrid_mcp.auth import auth_status

SERVICE_NAME = "linkedin-hybrid-mcp"
MILESTONE = "milestone-2"


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
        "notes": [
            "Milestone 2 adds local auth/session storage scaffolding.",
            "LinkedIn auth, browser bootstrap, refresh flows, and API integrations are still not implemented.",
        ],
    }


@mcp.tool()
def health() -> dict[str, str]:
    """Report basic service liveness metadata."""

    return health_payload()


@mcp.tool()
def service_info() -> dict[str, object]:
    """Describe the current scaffold and intended architecture."""

    return service_info_payload()
