from __future__ import annotations

import io
import socket
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from linkedin_hybrid_mcp.auth import SessionMetadata
from linkedin_hybrid_mcp.client import (
    AuthRequiredError,
    HttpStatusTransportError,
    NetworkTransportError,
    RequestBuildError,
    RequestSettings,
    ResponseTooLargeError,
    RetryPolicy,
    authenticated_request,
    build_authenticated_request,
    execute_request,
    sanitize_headers,
    transport_self_test,
)
from linkedin_hybrid_mcp.config import resolve_storage_paths


class FakeResponse:
    def __init__(
        self,
        *,
        url: str = "https://example.com/resource",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes = b"{}",
    ) -> None:
        self._url = url
        self._status_code = status_code
        self.headers = Message()
        for key, value in (headers or {"Content-Type": "application/json"}).items():
            self.headers[key] = value
        self._body = body

    def geturl(self) -> str:
        return self._url

    def getcode(self) -> int:
        return self._status_code

    def read(self, _limit: int | None = None) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FakeOpener:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, float | None]] = []

    def open(self, request, timeout=None):  # type: ignore[no-untyped-def]
        self.calls.append((request.full_url, timeout))
        next_item = self._responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


def make_ready_session() -> SessionMetadata:
    return SessionMetadata(
        login_state="bootstrapped",
        cookies_present=True,
        headers_present=True,
    )


def make_http_error(status_code: int, body: bytes = b"error") -> HTTPError:
    headers = Message()
    headers["Content-Type"] = "application/json"
    return HTTPError(
        url="https://example.com/resource",
        code=status_code,
        msg="failure",
        hdrs=headers,
        fp=io.BytesIO(body),
    )


def test_sanitize_headers_rejects_unsafe_names() -> None:
    with pytest.raises(RequestBuildError, match="managed by the HTTP client"):
        sanitize_headers({"Host": "evil.example"})


def test_sanitize_headers_rejects_newlines() -> None:
    with pytest.raises(RequestBuildError, match="unsafe newline"):
        sanitize_headers({"X-Test": "bad\nvalue"})


def test_build_authenticated_request_redacts_sensitive_headers(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    session = make_ready_session()

    request, diagnostics = build_authenticated_request(
        url="https://example.com/resource",
        auth_headers={"Authorization": "Bearer secret"},
        headers={"X-Trace-Id": "abc123"},
        auth=transport_self_test(session=session, paths=paths).auth,
    )

    assert request.get_method() == "GET"
    assert request.headers["Authorization"] == "Bearer secret"
    assert diagnostics.headers["Authorization"] == "<redacted>"
    assert diagnostics.headers["X-Trace-Id"] == "abc123"


def test_build_authenticated_request_requires_ready_auth() -> None:
    with pytest.raises(AuthRequiredError, match="Authenticated request blocked"):
        build_authenticated_request(
            url="https://example.com/resource",
            auth_headers={"Authorization": "Bearer secret"},
            auth=transport_self_test().auth,
        )


def test_build_authenticated_request_requires_explicit_auth_headers(tmp_path: Path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    session = make_ready_session()

    with pytest.raises(AuthRequiredError, match="require explicit auth headers"):
        build_authenticated_request(
            url="https://example.com/resource",
            auth_headers={},
            auth=transport_self_test(session=session, paths=paths).auth,
        )


def test_execute_request_returns_normalized_response() -> None:
    opener = FakeOpener([FakeResponse(body=b'{"ok":true}')])

    response = execute_request(
        build_authenticated_request(
            url="https://example.com/resource",
            auth_headers={"Authorization": "Bearer secret"},
            auth=transport_self_test(session=make_ready_session()).auth,
        )[0],
        opener=opener,
    )

    assert response.status_code == 200
    assert response.text() == '{"ok":true}'


def test_execute_request_retries_retryable_http_status() -> None:
    opener = FakeOpener([make_http_error(503), FakeResponse(body=b"ok")])
    sleeps: list[float] = []

    response = execute_request(
        build_authenticated_request(
            url="https://example.com/resource",
            auth_headers={"Authorization": "Bearer secret"},
            auth=transport_self_test(session=make_ready_session()).auth,
        )[0],
        opener=opener,
        retry_policy=RetryPolicy(max_attempts=2, initial_delay_seconds=0.5),
        sleep=sleeps.append,
    )

    assert response.body == b"ok"
    assert sleeps == [0.5]


def test_execute_request_raises_typed_http_error_after_retries() -> None:
    opener = FakeOpener([make_http_error(429), make_http_error(429)])

    with pytest.raises(HttpStatusTransportError) as exc_info:
        execute_request(
            build_authenticated_request(
                url="https://example.com/resource",
                auth_headers={"Authorization": "Bearer secret"},
                auth=transport_self_test(session=make_ready_session()).auth,
            )[0],
            opener=opener,
            retry_policy=RetryPolicy(max_attempts=2),
            sleep=lambda _seconds: None,
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.retryable is True


def test_execute_request_retries_timeout_errors() -> None:
    opener = FakeOpener([URLError(socket.timeout("timed out")), FakeResponse(body=b"ok")])
    sleeps: list[float] = []

    response = execute_request(
        build_authenticated_request(
            url="https://example.com/resource",
            auth_headers={"Authorization": "Bearer secret"},
            auth=transport_self_test(session=make_ready_session()).auth,
        )[0],
        opener=opener,
        retry_policy=RetryPolicy(max_attempts=2, initial_delay_seconds=0.2),
        sleep=sleeps.append,
    )

    assert response.body == b"ok"
    assert sleeps == [0.2]


def test_execute_request_raises_network_transport_error_for_non_retryable_url_error() -> None:
    opener = FakeOpener([URLError("dns failed")])

    with pytest.raises(NetworkTransportError, match="dns failed"):
        execute_request(
            build_authenticated_request(
                url="https://example.com/resource",
                auth_headers={"Authorization": "Bearer secret"},
                auth=transport_self_test(session=make_ready_session()).auth,
            )[0],
            opener=opener,
        )


def test_execute_request_enforces_response_size_limit() -> None:
    opener = FakeOpener([FakeResponse(body=b"012345")])

    with pytest.raises(ResponseTooLargeError):
        execute_request(
            build_authenticated_request(
                url="https://example.com/resource",
                auth_headers={"Authorization": "Bearer secret"},
                auth=transport_self_test(session=make_ready_session()).auth,
                settings=RequestSettings(max_response_bytes=5),
            )[0],
            opener=opener,
            settings=RequestSettings(max_response_bytes=5),
        )


def test_authenticated_request_uses_session_and_executes_call(tmp_path: Path) -> None:
    opener = FakeOpener([FakeResponse(body=b"ok")])
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    response = authenticated_request(
        url="https://example.com/resource",
        session=make_ready_session(),
        paths=paths,
        auth_headers={"Cookie": "li_at=secret"},
        opener=opener,
    )

    assert response.body == b"ok"
    assert opener.calls[0][1] == 30.0


def test_transport_self_test_reports_no_live_network_calls() -> None:
    result = transport_self_test(session=make_ready_session())

    assert result.can_attempt_authenticated_request is True
    assert "does not perform a live network call" in result.notes[0]
