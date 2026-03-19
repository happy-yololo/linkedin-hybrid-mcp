"""Production-shaped HTTP transport scaffolding for authenticated requests."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from email.message import Message
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import OpenerDirector, Request, build_opener

from linkedin_hybrid_mcp.auth import AuthStatus, SessionMetadata, auth_status
from linkedin_hybrid_mcp.config import StoragePaths

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024
DEFAULT_USER_AGENT = "linkedin-hybrid-mcp/0.1.0"
REDACTED_HEADER_NAMES = frozenset({"authorization", "cookie", "set-cookie", "proxy-authorization"})
UNSAFE_HEADER_NAMES = frozenset({"connection", "content-length", "host", "transfer-encoding"})


class TransportError(Exception):
    """Base class for typed transport failures."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class TransportConfigError(TransportError):
    """Raised for invalid transport configuration."""


class AuthRequiredError(TransportError):
    """Raised when authenticated requests are attempted without usable auth state."""


class RequestBuildError(TransportError):
    """Raised when request inputs are invalid or unsafe."""


class NetworkTransportError(TransportError):
    """Raised when a network call fails before a valid response is returned."""


class ResponseTooLargeError(TransportError):
    """Raised when the response exceeds configured memory limits."""


class HttpStatusTransportError(TransportError):
    """Raised when a non-successful HTTP status is returned."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_headers: Mapping[str, str] | None = None,
        response_body: bytes | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message, retryable=retryable)
        self.status_code = status_code
        self.response_headers = dict(response_headers or {})
        self.response_body = response_body


@dataclass(frozen=True)
class RequestSettings:
    """Per-request runtime limits and defaults."""

    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    user_agent: str = DEFAULT_USER_AGENT

    def validate(self) -> None:
        if self.timeout_seconds <= 0:
            raise TransportConfigError("timeout_seconds must be greater than zero.")
        if self.max_response_bytes <= 0:
            raise TransportConfigError("max_response_bytes must be greater than zero.")
        if not self.user_agent.strip():
            raise TransportConfigError("user_agent must not be empty.")


@dataclass(frozen=True)
class RetryPolicy:
    """Simple exponential backoff policy for idempotent transport retries."""

    max_attempts: int = 3
    initial_delay_seconds: float = 0.25
    backoff_multiplier: float = 2.0
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)
    retry_on_timeout: bool = True

    def validate(self) -> None:
        if self.max_attempts <= 0:
            raise TransportConfigError("max_attempts must be greater than zero.")
        if self.initial_delay_seconds < 0:
            raise TransportConfigError("initial_delay_seconds must be non-negative.")
        if self.backoff_multiplier < 1:
            raise TransportConfigError("backoff_multiplier must be at least one.")

    def delay_for_attempt(self, attempt_number: int) -> float:
        if attempt_number <= 1:
            return 0.0
        exponent = attempt_number - 2
        return self.initial_delay_seconds * (self.backoff_multiplier ** exponent)

    def is_retryable_status(self, status_code: int) -> bool:
        return status_code in self.retryable_status_codes


@dataclass(frozen=True)
class HttpResponse:
    """Normalized HTTP response container."""

    url: str
    status_code: int
    headers: dict[str, str]
    body: bytes

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding)


@dataclass(frozen=True)
class RequestDiagnostics:
    """Safe, loggable request metadata with secrets redacted."""

    method: str
    url: str
    headers: dict[str, str]
    timeout_seconds: float
    max_response_bytes: int


@dataclass(frozen=True)
class TransportSelfTestResult:
    """Self-test summary for current transport readiness."""

    auth: AuthStatus
    session_has_header_material: bool
    can_attempt_authenticated_request: bool
    request_settings: RequestSettings
    retry_policy: RetryPolicy
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "auth": self.auth.to_dict(),
            "session_has_header_material": self.session_has_header_material,
            "can_attempt_authenticated_request": self.can_attempt_authenticated_request,
            "request_settings": {
                "timeout_seconds": self.request_settings.timeout_seconds,
                "max_response_bytes": self.request_settings.max_response_bytes,
                "user_agent": self.request_settings.user_agent,
            },
            "retry_policy": {
                "max_attempts": self.retry_policy.max_attempts,
                "initial_delay_seconds": self.retry_policy.initial_delay_seconds,
                "backoff_multiplier": self.retry_policy.backoff_multiplier,
                "retryable_status_codes": list(self.retry_policy.retryable_status_codes),
                "retry_on_timeout": self.retry_policy.retry_on_timeout,
            },
            "notes": list(self.notes),
        }


def _normalize_header_name(name: str) -> str:
    return "-".join(part.capitalize() for part in name.strip().split("-"))


def sanitize_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    """Validate headers and strip unsafe values before request submission."""

    sanitized: dict[str, str] = {}
    if not headers:
        return sanitized

    for raw_name, raw_value in headers.items():
        name = raw_name.strip()
        value = raw_value.strip()
        lower_name = name.lower()
        if not name:
            raise RequestBuildError("Header names must not be empty.")
        if lower_name in UNSAFE_HEADER_NAMES:
            raise RequestBuildError(f"Header '{name}' is managed by the HTTP client and cannot be set.")
        if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
            raise RequestBuildError(f"Header '{name}' contains an unsafe newline sequence.")
        sanitized[_normalize_header_name(name)] = value

    return sanitized


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a safe representation of request headers for logs or tool output."""

    redacted: dict[str, str] = {}
    for name, value in headers.items():
        if name.lower() in REDACTED_HEADER_NAMES:
            redacted[name] = "<redacted>"
        else:
            redacted[name] = value
    return redacted


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RequestBuildError("Only absolute http(s) URLs are supported.")


def _coerce_headers(message: Message) -> dict[str, str]:
    return {key: value for key, value in message.items()}


def build_authenticated_request(
    *,
    url: str,
    auth: AuthStatus,
    auth_headers: Mapping[str, str],
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    data: bytes | None = None,
    settings: RequestSettings | None = None,
) -> tuple[Request, RequestDiagnostics]:
    """Construct a safe generic authenticated request.

    Callers must supply explicit auth headers. This scaffold does not read or
    reconstruct private LinkedIn session material from local storage.
    """

    request_settings = settings or RequestSettings()
    request_settings.validate()
    _validate_url(url)

    normalized_method = method.upper().strip()
    if not normalized_method:
        raise RequestBuildError("HTTP method must not be empty.")
    if not auth.can_attempt_http:
        raise AuthRequiredError(f"Authenticated request blocked: {auth.summary}")

    sanitized_auth_headers = sanitize_headers(auth_headers)
    if not sanitized_auth_headers:
        raise AuthRequiredError("Authenticated requests require explicit auth headers.")

    combined_headers = sanitize_headers(headers)
    combined_headers.update(sanitized_auth_headers)
    combined_headers.setdefault("User-Agent", request_settings.user_agent)

    request = Request(url=url, data=data, headers=combined_headers, method=normalized_method)
    diagnostics = RequestDiagnostics(
        method=normalized_method,
        url=url,
        headers=redact_headers(combined_headers),
        timeout_seconds=request_settings.timeout_seconds,
        max_response_bytes=request_settings.max_response_bytes,
    )
    return request, diagnostics


def execute_request(
    request: Request,
    *,
    settings: RequestSettings | None = None,
    retry_policy: RetryPolicy | None = None,
    opener: OpenerDirector | Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> HttpResponse:
    """Execute an HTTP request with size limits and retry/backoff handling."""

    request_settings = settings or RequestSettings()
    active_retry_policy = retry_policy or RetryPolicy()
    request_settings.validate()
    active_retry_policy.validate()
    http_opener = opener or build_opener()

    for attempt_number in range(1, active_retry_policy.max_attempts + 1):
        if attempt_number > 1:
            sleep(active_retry_policy.delay_for_attempt(attempt_number))

        try:
            with http_opener.open(request, timeout=request_settings.timeout_seconds) as response:
                body = response.read(request_settings.max_response_bytes + 1)
                if len(body) > request_settings.max_response_bytes:
                    raise ResponseTooLargeError(
                        "Response exceeded max_response_bytes.",
                        retryable=False,
                    )
                return HttpResponse(
                    url=response.geturl(),
                    status_code=response.getcode(),
                    headers=_coerce_headers(response.headers),
                    body=body,
                )
        except HTTPError as exc:
            body = exc.read()
            response_headers = _coerce_headers(exc.headers)
            retryable = active_retry_policy.is_retryable_status(exc.code)
            error = HttpStatusTransportError(
                f"HTTP request failed with status {exc.code}.",
                status_code=exc.code,
                response_headers=response_headers,
                response_body=body,
                retryable=retryable,
            )
            if retryable and attempt_number < active_retry_policy.max_attempts:
                continue
            raise error from exc
        except URLError as exc:
            reason = exc.reason
            retryable = isinstance(reason, socket.timeout) and active_retry_policy.retry_on_timeout
            error = NetworkTransportError(
                f"HTTP request failed before receiving a response: {reason}",
                retryable=retryable,
            )
            if retryable and attempt_number < active_retry_policy.max_attempts:
                continue
            raise error from exc


def authenticated_request(
    *,
    url: str,
    session: SessionMetadata | None = None,
    paths: StoragePaths | None = None,
    auth_headers: Mapping[str, str],
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    data: bytes | None = None,
    settings: RequestSettings | None = None,
    retry_policy: RetryPolicy | None = None,
    opener: OpenerDirector | Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> HttpResponse:
    """Perform a generic authenticated request using current local auth state."""

    current_auth = auth_status(session=session, paths=paths)
    request, _ = build_authenticated_request(
        url=url,
        auth=current_auth,
        auth_headers=auth_headers,
        method=method,
        headers=headers,
        data=data,
        settings=settings,
    )
    return execute_request(
        request,
        settings=settings,
        retry_policy=retry_policy,
        opener=opener,
        sleep=sleep,
    )


def transport_self_test(
    *,
    session: SessionMetadata | None = None,
    paths: StoragePaths | None = None,
    request_settings: RequestSettings | None = None,
    retry_policy: RetryPolicy | None = None,
) -> TransportSelfTestResult:
    """Return non-network transport readiness diagnostics."""

    current_auth = auth_status(session=session, paths=paths)
    active_request_settings = request_settings or RequestSettings()
    active_retry_policy = retry_policy or RetryPolicy()
    active_request_settings.validate()
    active_retry_policy.validate()

    session_has_header_material = bool(session.headers_present) if session is not None else False

    return TransportSelfTestResult(
        auth=current_auth,
        session_has_header_material=session_has_header_material,
        can_attempt_authenticated_request=current_auth.can_attempt_http and session_has_header_material,
        request_settings=active_request_settings,
        retry_policy=active_retry_policy,
        notes=(
            "This self-test does not perform a live network call.",
            "Authenticated requests still require explicit caller-supplied auth headers.",
        ),
    )
