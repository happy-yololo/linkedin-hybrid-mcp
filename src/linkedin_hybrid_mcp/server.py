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
    OperationLookupError,
    PersonProfileRequest,
    SearchJobsRequest,
    SearchPeopleRequest,
    benchmark_operations,
    company_posts_blocked_result,
)
from linkedin_hybrid_mcp.public_features import (
    DuckDuckGoLinkedInPeopleSearchProvider,
    LinkedInPublicJobDetailsProvider,
    LinkedInPublicJobsSearchProvider,
    LinkedInPublicPersonProfileProvider,
)

SERVICE_NAME = "linkedin-hybrid-mcp"
MILESTONE = "milestone-8"


def _public_web_enabled() -> bool:
    return os.getenv("LINKEDIN_HYBRID_ENABLE_PUBLIC_WEB", "").strip() == "1"


def _company_profile_enabled() -> bool:
    return os.getenv("LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC", "").strip() == "1"


def _implemented_operations() -> list[str]:
    operations: list[str] = []
    if _public_web_enabled():
        operations.extend(
            [
                "search_people",
                "get_person_profile",
                "search_jobs",
                "get_job_details",
            ]
        )
    if _company_profile_enabled():
        operations.append("get_company_profile")
    return operations


def _build_feature_parity_service() -> LinkedInFeatureParityService:
    options: dict[str, object] = {}
    if _public_web_enabled():
        options.update(
            {
                "search_people_provider": DuckDuckGoLinkedInPeopleSearchProvider(),
                "person_profile_provider": LinkedInPublicPersonProfileProvider(),
                "search_jobs_provider": LinkedInPublicJobsSearchProvider(),
                "job_details_provider": LinkedInPublicJobDetailsProvider(),
            }
        )
    if _company_profile_enabled():
        options["company_profile_provider"] = LinkedInPublicCompanyProfileProvider()
    return LinkedInFeatureParityService(**options)


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
                "public-web integration enabled for selected operations; unlisted operations remain placeholders"
                if _implemented_operations()
                else "placeholder domain/service layer only (public-web integrations are opt-in)"
            ),
            "operations": benchmark_operations(),
        },
        "notes": [
            "Milestone 8 adds public-web providers for people/profile/jobs operations behind explicit opt-in flags.",
            "LinkedIn auth, browser bootstrap, refresh flows, and LinkedIn private API integrations are still not implemented.",
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

    implemented_operations = _implemented_operations()
    placeholder_operations = [
        operation for operation in benchmark_operations() if operation not in implemented_operations
    ]
    return {
        "service": SERVICE_NAME,
        "milestone": MILESTONE,
        "benchmark": FEATURE_BENCHMARK,
        "implemented": bool(implemented_operations),
        "implemented_operations": implemented_operations,
        "placeholder_operations": placeholder_operations,
        "operations": benchmark_operations(),
        "notes": [
            "Implemented operations use public pages/public search only and are enabled explicitly by environment flags.",
            "get_company_posts remains blocked due dynamic feed rendering and no browser/auth fallback in this repository.",
            "This service does not claim LinkedIn private API, scraping automation, or browser execution support.",
        ],
    }


def search_people_payload(*, query: str, limit: int = 10) -> dict[str, object]:
    """Return public-search people results when enabled, otherwise fail safely."""

    request = SearchPeopleRequest(query=query, limit=limit)
    try:
        result = feature_parity_service.search_people(request)
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "search_people",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "implemented",
                "summary": "Returns public web search hits for LinkedIn profile URLs.",
                "request": {"query": request.query, "limit": request.limit},
                "notes": [
                    "This path uses public web indexing only and does not use LinkedIn private APIs.",
                    "Results may be incomplete depending on public indexing coverage.",
                ],
            },
            "people_search": result.to_dict(),
        }
    except OperationLookupError as exc:
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "search_people",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "lookup_failed",
                "summary": "People search integration is configured but the lookup failed.",
                "request": {"query": request.query, "limit": request.limit},
                "retryable": exc.retryable,
                "error": str(exc),
            },
        }
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "search_people",
            {"query": request.query, "limit": request.limit},
        )


def get_person_profile_payload(*, person_id: str) -> dict[str, object]:
    """Return public-profile data when enabled, otherwise fail safely."""

    request = PersonProfileRequest(person_id=person_id)
    try:
        profile = feature_parity_service.get_person_profile(request)
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "get_person_profile",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "implemented",
                "summary": "Returns person profile metadata parsed from public LinkedIn profile page HTML.",
                "request": {"person_id": request.person_id},
                "notes": [
                    "Implementation parses Open Graph and JSON-LD metadata from publicly visible profile pages.",
                    "Profiles with limited public visibility may return fewer fields.",
                ],
            },
            "person_profile": profile.to_dict(),
        }
    except OperationLookupError as exc:
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "get_person_profile",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "lookup_failed",
                "summary": "Person profile integration is configured but the profile lookup failed.",
                "request": {"person_id": request.person_id},
                "retryable": exc.retryable,
                "error": str(exc),
            },
        }
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "get_person_profile",
            {"person_id": request.person_id},
        )


def search_jobs_payload(*, query: str, location: str | None = None, limit: int = 10) -> dict[str, object]:
    """Return public jobs search results when enabled, otherwise fail safely."""

    request = SearchJobsRequest(query=query, location=location, limit=limit)
    try:
        result = feature_parity_service.search_jobs(request)
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "search_jobs",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "implemented",
                "summary": "Returns job hits parsed from public LinkedIn jobs search pages.",
                "request": {
                    "query": request.query,
                    "location": request.location,
                    "limit": request.limit,
                },
                "notes": [
                    "This path uses public LinkedIn jobs pages and metadata only.",
                    "No LinkedIn private API access is used.",
                ],
            },
            "jobs_search": result.to_dict(),
        }
    except OperationLookupError as exc:
        payload: dict[str, object] = {"query": request.query, "limit": request.limit}
        if request.location is not None:
            payload["location"] = request.location
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "search_jobs",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "lookup_failed",
                "summary": "Jobs search integration is configured but the search lookup failed.",
                "request": payload,
                "retryable": exc.retryable,
                "error": str(exc),
            },
        }
    except DomainOperationNotImplementedError:
        payload: dict[str, object] = {"query": request.query, "limit": request.limit}
        if request.location is not None:
            payload["location"] = request.location
        return _unimplemented_feature_payload("search_jobs", payload)


def get_job_details_payload(*, job_id: str) -> dict[str, object]:
    """Return public job details when enabled, otherwise fail safely."""

    request = JobDetailsRequest(job_id=job_id)
    try:
        details = feature_parity_service.get_job_details(request)
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "get_job_details",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "implemented",
                "summary": "Returns job details parsed from public LinkedIn job page metadata.",
                "request": {"job_id": request.job_id},
                "notes": [
                    "Implementation parses Open Graph and JSON-LD JobPosting metadata only.",
                    "No authenticated or private API calls are performed.",
                ],
            },
            "job_details": details.to_dict(),
        }
    except OperationLookupError as exc:
        return {
            "service": SERVICE_NAME,
            "milestone": MILESTONE,
            "feature": {
                "operation": "get_job_details",
                "benchmark": FEATURE_BENCHMARK,
                "implemented": True,
                "status": "lookup_failed",
                "summary": "Job details integration is configured but the detail lookup failed.",
                "request": {"job_id": request.job_id},
                "retryable": exc.retryable,
                "error": str(exc),
            },
        }
    except DomainOperationNotImplementedError:
        return _unimplemented_feature_payload(
            "get_job_details",
            {"job_id": request.job_id},
        )


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
    """Fail safely with explicit blockers for company posts."""

    request = CompanyPostsRequest(company_id=company_id, limit=limit)
    blocked = company_posts_blocked_result(request)
    try:
        feature_parity_service.get_company_posts(request)
    except DomainOperationNotImplementedError:
        payload = _unimplemented_feature_payload(
            "get_company_posts",
            {"company_id": blocked.company_id, "limit": blocked.limit},
        )
        payload["feature"]["blockers"] = [item.to_dict() for item in blocked.blockers]
        payload["feature"]["attempted_public_urls"] = list(blocked.attempted_public_urls)
        payload["feature"]["required_next_capabilities"] = list(blocked.required_next_capabilities)
        payload["feature"]["next_honest_steps"] = list(blocked.next_honest_steps)
        payload["feature"]["notes"] = [
            *payload["feature"]["notes"],
            *blocked.notes,
        ]
        return payload
    raise AssertionError("get_company_posts should fail closed when no provider is configured.")


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
    """Search public web sources for LinkedIn profile hits."""

    return search_people_payload(query=query, limit=limit)


@mcp.tool()
def get_person_profile(person_id: str) -> dict[str, object]:
    """Fetch public LinkedIn profile metadata when integration is enabled."""

    return get_person_profile_payload(person_id=person_id)


@mcp.tool()
def search_jobs(query: str, location: str | None = None, limit: int = 10) -> dict[str, object]:
    """Search public LinkedIn jobs pages when integration is enabled."""

    return search_jobs_payload(query=query, location=location, limit=limit)


@mcp.tool()
def get_job_details(job_id: str) -> dict[str, object]:
    """Fetch public LinkedIn job detail metadata when integration is enabled."""

    return get_job_details_payload(job_id=job_id)


@mcp.tool()
def get_company_profile(company_id: str) -> dict[str, object]:
    """Return a safe not-implemented payload for benchmarked company profile lookup."""

    return get_company_profile_payload(company_id=company_id)


@mcp.tool()
def get_company_posts(company_id: str, limit: int = 10) -> dict[str, object]:
    """Return explicit blockers for company posts until a stable public source exists."""

    return get_company_posts_payload(company_id=company_id, limit=limit)
