from linkedin_hybrid_mcp.server import health_payload, service_info_payload


def test_health_payload() -> None:
    payload = health_payload()

    assert payload["status"] == "ok"
    assert payload["service"] == "linkedin-hybrid-mcp"


def test_service_info_payload_marks_scaffold() -> None:
    payload = service_info_payload()

    assert payload["milestone"] == "milestone-2"
    assert payload["architecture"]["mode"] == "api-first"
    assert payload["architecture"]["implemented"] == "partial"
    assert payload["auth"]["implemented"] == "local session scaffold only"
