"""Minimal MCP server skeleton for current milestone."""

from __future__ import annotations

import os
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
from linkedin_hybrid_mcp.company_profile import LinkedInPublicCompanyProfileProvider
from linkedin_hybrid_mcp.client import transport_self_test
from linkedin_hybrid_mcp.config import StoragePaths
from linkedin_hybrid_mcp.domain import (
    FEATURE_BENCHMARK,
    CompanyProfileLookupError,
    CompanyPostsRequest,
    CompanyProfileRequest,
    DomainOperationNotImplementedError,
    JobDetailsRequest,
    LinkedInFeatureParityService,
    PersonProfileRequest,
    SearchJobsRequest,
    SearchPeopleRequest,
    benchmark_operations,
)

SERVICE_NAME = "linkedin-hybrid-mcp"
MILESTONE = "milestone-7"


def _build_feature_parity_service() -> LinkedInFeatureParityService:
    if os.getenv("LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC", "").strip() == "1":
        return LinkedInFeatureParityService(
            company_profile_provider=LinkedInPublicCompanyProfileProvider(),
        )
    return LinkedInFeatureParityService()


feature_parity_service = _build_feature_parity_service()


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
        "feature_parity": {
            "benchmark": FEATURE_BENCHMARK,
            "implemented": (
                "company profile integration enabled; remaining operations are placeholders"
                if os.getenv("LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC", "").strip() == "1"
                else "placeholder domain/service layer only (company profile has opt-in integration)"
            ),
            "operations": benchmark_operations(),
        },
        "notes": [
            "Milestone 7 adds typed benchmark operation interfaces and a real company profile integration path.",
            "LinkedIn auth, browser bootstrap, refresh flows, and most LinkedIn-specific API integrations are still not implemented.",
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
        "feature_parity": feature_parity_payload(),
    }


def _unimplemented_feature_payload(
    operation_name: str,
    request: dict[str, object],
) -> dict[str, object]:
    placeholder = feature_parity_service.placeholder_for(operation_name, request=request)
    return {
        "service": SERVICE_NAME,
        "milestone": MILESTONE,
        "feature": placeholder.to_dict(),
    }


def feature_parity_payload() -> dict[str, object]:
    """Describe the benchmarked LinkedIn operations tracked by placeholders."""

    company_profile_enabled = (
        os.getenv("LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC", "").strip() == "1"
    )
    return {
        "service": SERVICE_NAME,
        "milestone": MILESTONE,
        "benchmark": FEATURE_BENCHMARK,
        "implemented": company_profile_enabled,
        "implemented_operations": ["get_company_profile"] if company_profile_enabled else [],
        "placeholder_operations": [
            "search_people",
            "get_person_profile",
            "search_jobs",
            "get_job_details",
            "get_company_posts",
        ]
        if company_profile_enabled
        else benchmark_operations(),
        "operations": benchmark_operations(),
        "notes": [
            "get_company_profile has a real opt-in integration path via LinkedIn public company page metadata.",
            "Other operations are tracked as explicit placeholders only.",
            "The current scaffold does not claim LinkedIn private API, scraping, or browser execution support.",
        ],
    }


def search_people_payload(*, query: str, limit: int = 10) -> dict[str, object]:
    """Fail safely for the benchmarked people search operation."""

    request = SearchPeopleRequest(query=query, limit=limit)
    try:
        feature_parity_service.search_people(request)
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "search_people",
            {"query": request.query, "limit": request.limit},
        )
    raise AssertionError("search_people placeholder should always raise not implemented.")


def get_person_profile_payload(*, person_id: str) -> dict[str, object]:
    """Fail safely for the benchmarked person profile operation."""

    request = PersonProfileRequest(person_id=person_id)
    try:
        feature_parity_service.get_person_profile(request)
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "get_person_profile",
            {"person_id": request.person_id},
        )
    raise AssertionError("get_person_profile placeholder should always raise not implemented.")


def search_jobs_payload(*, query: str, location: str | None = None, limit: int = 10) -> dict[str, object]:
    """Fail safely for the benchmarked job search operation."""

    request = SearchJobsRequest(query=query, location=location, limit=limit)
    try:
        feature_parity_service.search_jobs(request)
    except DomainOperationNotImplementedError:
        payload: dict[str, object] = {"query": request.query, "limit": request.limit}
        if request.location is not None:
            payload["location"] = request.location
        return _unimplemented_feature_payload("search_jobs", payload)
    raise AssertionError("search_jobs placeholder should always raise not implemented.")


def get_job_details_payload(*, job_id: str) -> dict[str, object]:
    """Fail safely for the benchmarked job details operation."""

    request = JobDetailsRequest(job_id=job_id)
    try:
        feature_parity_service.get_job_details(request)
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "get_job_details",
            {"job_id": request.job_id},
        )
    raise AssertionError("get_job_details placeholder should always raise not implemented.")


def get_company_profile_payload(*, company_id: str) -> dict[str, object]:
    """Return company profile data when configured, otherwise fail safely."""

    request = CompanyProfileRequest(company_id=company_id)
    try:
        profile = feature_parity_service.get_company_profile(request)
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "get_company_profile",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "implemented",
                "summary": (
                    "Returns company profile metadata parsed from LinkedIn public company page HTML."
                ),
                "request": {"company_id": request.company_id},
                "notes": [
                    "Implementation is API-first HTTP fetch + metadata parsing; no browser automation.",
                    "Coverage depends on what metadata LinkedIn exposes publicly for the target company page.",
                ],
            },
            "company_profile": profile.to_dict(),
        }
    except CompanyProfileLookupError as exc:
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "get_company_profile",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "lookup_failed",
                "summary": "Company profile integration is configured but the profile lookup failed.",
                "request": {"company_id": request.company_id},
                "retryable": exc.retryable,
                "error": str(exc),
                "notes": [
                    "This is a real integration path, but LinkedIn availability/shape can still fail at runtime.",
                ],
            },
        }
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "get_company_profile",
            {"company_id": request.company_id},
        )


def get_company_posts_payload(*, company_id: str, limit: int = 10) -> dict[str, object]:
    """Fail safely for the benchmarked company posts operation."""

    request = CompanyPostsRequest(company_id=company_id, limit=limit)
    try:
        feature_parity_service.get_company_posts(request)
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "get_company_posts",
            {"company_id": request.company_id, "limit": request.limit},
        )
    raise AssertionError("get_company_posts placeholder should always raise not implemented.")


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


@mcp.tool()
def feature_parity_status() -> dict[str, object]:
    """Describe benchmarked LinkedIn operations that remain placeholders."""

    return feature_parity_payload()


@mcp.tool()
def search_people(query: str, limit: int = 10) -> dict[str, object]:
    """Return a safe not-implemented payload for benchmarked people search."""

    return search_people_payload(query=query, limit=limit)


@mcp.tool()
def get_person_profile(person_id: str) -> dict[str, object]:
    """Return a safe not-implemented payload for benchmarked profile lookup."""

    return get_person_profile_payload(person_id=person_id)


@mcp.tool()
def search_jobs(query: str, location: str | None = None, limit: int = 10) -> dict[str, object]:
    """Return a safe not-implemented payload for benchmarked job search."""

    return search_jobs_payload(query=query, location=location, limit=limit)


@mcp.tool()
def get_job_details(job_id: str) -> dict[str, object]:
    """Return a safe not-implemented payload for benchmarked job detail lookup."""

    return get_job_details_payload(job_id=job_id)


@mcp.tool()
def get_company_profile(company_id: str) -> dict[str, object]:
    """Return a safe not-implemented payload for benchmarked company profile lookup."""

    return get_company_profile_payload(company_id=company_id)


@mcp.tool()
def get_company_posts(company_id: str, limit: int = 10) -> dict[str, object]:
    """Return a safe not-implemented payload for benchmarked company posts lookup."""

    return get_company_posts_payload(company_id=company_id, limit=limit)
