"""Typed LinkedIn domain-operation placeholders for honest feature parity tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FEATURE_BENCHMARK = "linkedin-mcp-server"


class DomainOperationNotImplementedError(NotImplementedError):
    """Raised when a benchmarked LinkedIn operation is intentionally unimplemented."""

    def __init__(self, operation_name: str, message: str) -> None:
        super().__init__(message)
        self.operation_name = operation_name


@dataclass(frozen=True)
class SearchPeopleRequest:
    query: str
    limit: int = 10


@dataclass(frozen=True)
class PersonProfileRequest:
    person_id: str


@dataclass(frozen=True)
class SearchJobsRequest:
    query: str
    location: str | None = None
    limit: int = 10


@dataclass(frozen=True)
class JobDetailsRequest:
    job_id: str


@dataclass(frozen=True)
class CompanyProfileRequest:
    company_id: str


@dataclass(frozen=True)
class CompanyPostsRequest:
    company_id: str
    limit: int = 10


@dataclass(frozen=True)
class OperationPlaceholder:
    """Safe description of a benchmarked but unimplemented operation."""

    operation_name: str
    benchmark: str
    implemented: bool
    summary: str
    request: dict[str, Any]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation_name,
            "benchmark": self.benchmark,
            "implemented": self.implemented,
            "status": "not_implemented",
            "summary": self.summary,
            "request": dict(self.request),
            "notes": list(self.notes),
        }


def _validate_non_empty(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty.")
    return normalized


def _validate_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return limit


class LinkedInFeatureParityService:
    """Explicit placeholder service for benchmarked LinkedIn operations."""

    def _raise_not_implemented(
        self,
        operation_name: str,
        *,
        request: dict[str, Any],
    ) -> None:
        raise DomainOperationNotImplementedError(
            operation_name,
            (
                f"{operation_name} is not implemented in this repository. "
                "The current scaffold does not claim LinkedIn private API or scraping support."
            ),
        )

    def placeholder_for(
        self,
        operation_name: str,
        *,
        request: dict[str, Any],
    ) -> OperationPlaceholder:
        return OperationPlaceholder(
            operation_name=operation_name,
            benchmark=FEATURE_BENCHMARK,
            implemented=False,
            summary=(
                f"{operation_name} is tracked for feature parity against "
                f"{FEATURE_BENCHMARK} but is intentionally unimplemented."
            ),
            request=request,
            notes=(
                "This placeholder fails closed and does not perform network access.",
                "No LinkedIn private API integration is claimed.",
                "No scraping or browser automation support is claimed for this operation.",
            ),
        )

    def search_people(self, request: SearchPeopleRequest) -> None:
        self._raise_not_implemented(
            "search_people",
            request={"query": _validate_non_empty("query", request.query), "limit": _validate_limit(request.limit)},
        )

    def get_person_profile(self, request: PersonProfileRequest) -> None:
        self._raise_not_implemented(
            "get_person_profile",
            request={"person_id": _validate_non_empty("person_id", request.person_id)},
        )

    def search_jobs(self, request: SearchJobsRequest) -> None:
        payload = {"query": _validate_non_empty("query", request.query), "limit": _validate_limit(request.limit)}
        if request.location is not None:
            payload["location"] = _validate_non_empty("location", request.location)
        self._raise_not_implemented("search_jobs", request=payload)

    def get_job_details(self, request: JobDetailsRequest) -> None:
        self._raise_not_implemented(
            "get_job_details",
            request={"job_id": _validate_non_empty("job_id", request.job_id)},
        )

    def get_company_profile(self, request: CompanyProfileRequest) -> None:
        self._raise_not_implemented(
            "get_company_profile",
            request={"company_id": _validate_non_empty("company_id", request.company_id)},
        )

    def get_company_posts(self, request: CompanyPostsRequest) -> None:
        self._raise_not_implemented(
            "get_company_posts",
            request={"company_id": _validate_non_empty("company_id", request.company_id), "limit": _validate_limit(request.limit)},
        )


def benchmark_operations() -> list[str]:
    """Return the benchmarked operation names tracked in this repository."""

    return [
        "search_people",
        "get_person_profile",
        "search_jobs",
        "get_job_details",
        "get_company_profile",
        "get_company_posts",
    ]
