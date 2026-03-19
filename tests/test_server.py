from __future__ import annotations

from linkedin_hybrid_mcp.auth import SessionMetadata, save_session
from linkedin_hybrid_mcp.config import resolve_storage_paths
from linkedin_hybrid_mcp.server import (
    auth_flow_placeholders_payload,
    auth_status_payload,
    clear_session_payload,
    health_payload,
    service_diagnostics_payload,
    service_info_payload,
    transport_diagnostics_payload,
)


def test_health_payload() -> None:
    payload = health_payload()

    assert payload["status"] == "ok"
    assert payload["service"] == "linkedin-hybrid-mcp"


def test_service_info_payload_marks_scaffold() -> None:
    payload = service_info_payload()

    assert payload["milestone"] == "milestone-4"
    assert payload["architecture"]["mode"] == "api-first"
    assert payload["architecture"]["implemented"] == "partial"
    assert payload["auth"]["implemented"] == "local session scaffold only"
    assert payload["transport"]["implemented"] == "generic authenticated request scaffold only"


def test_auth_status_payload_reports_local_readiness(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = auth_status_payload(paths=paths)

    assert payload["auth"]["state"] == "missing"
    assert "local session metadata readiness only" in payload["notes"][0]


def test_transport_diagnostics_payload_stays_non_network(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = transport_diagnostics_payload(paths=paths)

    assert payload["transport"]["auth"]["state"] == "missing"
    assert payload["runtime"]["tool_wrapper_mode"] in {"fastmcp", "import-only"}
    assert "does not make live network calls" in payload["notes"][0]


def test_clear_session_payload_reports_before_and_after(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    save_session(
        SessionMetadata(login_state="bootstrapped", cookies_present=True, headers_present=True),
        paths,
    )

    payload = clear_session_payload(paths=paths)

    assert payload["cleared"] is True
    assert payload["auth_before"]["state"] == "ready"
    assert payload["auth_after"]["state"] == "missing"
    assert paths.session_file.exists() is False


def test_auth_flow_placeholders_payload_surfaces_stub_messages(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = auth_flow_placeholders_payload(paths=paths)

    assert payload["bootstrap"]["implemented"] is False
    assert payload["bootstrap"]["status"] == "not_implemented"
    assert "Browser bootstrap is not implemented" in payload["bootstrap"]["message"]
    assert "Session refresh is not implemented" in payload["refresh"]["message"]


def test_service_diagnostics_payload_combines_subpayloads(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = service_diagnostics_payload(paths=paths)

    assert payload["milestone"] == "milestone-4"
    assert payload["auth_status"]["auth"]["state"] == "missing"
    assert payload["transport_self_test"]["transport"]["auth"]["state"] == "missing"
    assert payload["auth_placeholders"]["bootstrap"]["implemented"] is False
