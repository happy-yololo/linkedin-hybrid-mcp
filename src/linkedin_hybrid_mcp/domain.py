"""Typed LinkedIn domain-operation placeholders for honest feature parity tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

FEATURE_BENCHMARK = "linkedin-mcp-server"


class DomainOperationNotImplementedError(NotImplementedError):
    """Raised when a benchmarked LinkedIn operation is intentionally unimplemented."""

    def __init__(self, operation_name: str, message: str) -> None:
        super().__init__(message)
        self.operation_name = operation_name


class OperationLookupError(RuntimeError):
    """Raised when an operation is implemented but a runtime lookup fails."""

    def __init__(self, operation_name: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.operation_name = operation_name
        self.retryable = retryable


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
class CompanyProfileResult:
    company_id: str
    canonical_url: str
    name: str
    description: str | None = None
    website: str | None = None
    industry: str | None = None
    logo_url: str | None = None
    source: str = "linkedin_public_company_page"
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "canonical_url": self.canonical_url,
            "name": self.name,
            "description": self.description,
            "website": self.website,
            "industry": self.industry,
            "logo_url": self.logo_url,
            "source": self.source,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class PersonSearchHit:
    person_id: str
    profile_url: str
    name: str
    headline: str | None = None
    location: str | None = None
    source: str = "public_web_search"

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "profile_url": self.profile_url,
            "name": self.name,
            "headline": self.headline,
            "location": self.location,
            "source": self.source,
        }


@dataclass(frozen=True)
class SearchPeopleResult:
    query: str
    limit: int
    hits: tuple[PersonSearchHit, ...]
    source: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "limit": self.limit,
            "hits": [hit.to_dict() for hit in self.hits],
            "source": self.source,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class PersonProfileResult:
    person_id: str
    canonical_url: str
    name: str
    headline: str | None = None
    about: str | None = None
    location: str | None = None
    profile_image_url: str | None = None
    source: str = "linkedin_public_profile_page"
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "canonical_url": self.canonical_url,
            "name": self.name,
            "headline": self.headline,
            "about": self.about,
            "location": self.location,
            "profile_image_url": self.profile_image_url,
            "source": self.source,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class JobSearchHit:
    job_id: str
    job_url: str
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    source: str = "linkedin_public_jobs_search"

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_url": self.job_url,
            "title": self.title,
            "company_name": self.company_name,
            "location": self.location,
            "source": self.source,
        }


@dataclass(frozen=True)
class SearchJobsResult:
    query: str
    location: str | None
    limit: int
    hits: tuple[JobSearchHit, ...]
    source: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "location": self.location,
            "limit": self.limit,
            "hits": [hit.to_dict() for hit in self.hits],
            "source": self.source,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class JobDetailsResult:
    job_id: str
    job_url: str
    title: str
    company_name: str | None = None
    location: str | None = None
    description: str | None = None
    date_posted: str | None = None
    employment_type: str | None = None
    source: str = "linkedin_public_job_page"
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_url": self.job_url,
            "title": self.title,
            "company_name": self.company_name,
            "location": self.location,
            "description": self.description,
            "date_posted": self.date_posted,
            "employment_type": self.employment_type,
            "source": self.source,
            "notes": list(self.notes),
        }


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


class CompanyProfileLookupError(RuntimeError):
    """Raised when company profile retrieval fails after integration is configured."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class SearchPeopleProvider(Protocol):
    """Boundary interface for people search integrations."""

    def search_people(self, request: SearchPeopleRequest) -> SearchPeopleResult:
        """Find public person profiles for a text query."""


class PersonProfileProvider(Protocol):
    """Boundary interface for person profile retrieval integrations."""

    def get_person_profile(self, request: PersonProfileRequest) -> PersonProfileResult:
        """Fetch person profile details for a normalized profile identifier."""


class SearchJobsProvider(Protocol):
    """Boundary interface for jobs search integrations."""

    def search_jobs(self, request: SearchJobsRequest) -> SearchJobsResult:
        """Find public job postings for a query and optional location."""


class JobDetailsProvider(Protocol):
    """Boundary interface for job details retrieval integrations."""

    def get_job_details(self, request: JobDetailsRequest) -> JobDetailsResult:
        """Fetch a single job posting detail payload."""


class CompanyProfileProvider(Protocol):
    """Boundary interface for company profile retrieval integrations."""

    def get_company_profile(self, request: CompanyProfileRequest) -> CompanyProfileResult:
        """Fetch company profile details for a normalized company identifier."""


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

    def __init__(
        self,
        *,
        search_people_provider: SearchPeopleProvider | None = None,
        person_profile_provider: PersonProfileProvider | None = None,
        search_jobs_provider: SearchJobsProvider | None = None,
        job_details_provider: JobDetailsProvider | None = None,
        company_profile_provider: CompanyProfileProvider | None = None,
    ) -> None:
        self._search_people_provider = search_people_provider
        self._person_profile_provider = person_profile_provider
        self._search_jobs_provider = search_jobs_provider
        self._job_details_provider = job_details_provider
        self._company_profile_provider = company_profile_provider

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

    def search_people(self, request: SearchPeopleRequest) -> SearchPeopleResult:
        normalized_query = _validate_non_empty("query", request.query)
        normalized_limit = _validate_limit(request.limit)
        if self._search_people_provider is None:
            self._raise_not_implemented(
                "search_people",
                request={"query": normalized_query, "limit": normalized_limit},
            )
        try:
            return self._search_people_provider.search_people(
                SearchPeopleRequest(query=normalized_query, limit=normalized_limit)
            )
        except OperationLookupError:
            raise
        except Exception as exc:
            raise OperationLookupError(
                "search_people",
                f"Public people search failed for query '{normalized_query}': {exc}",
                retryable=False,
            ) from exc

    def get_person_profile(self, request: PersonProfileRequest) -> PersonProfileResult:
        normalized_person_id = _validate_non_empty("person_id", request.person_id)
        if self._person_profile_provider is None:
            self._raise_not_implemented(
                "get_person_profile",
                request={"person_id": normalized_person_id},
            )
        try:
            return self._person_profile_provider.get_person_profile(
                PersonProfileRequest(person_id=normalized_person_id)
            )
        except OperationLookupError:
            raise
        except Exception as exc:
            raise OperationLookupError(
                "get_person_profile",
                f"Person profile lookup failed for '{normalized_person_id}': {exc}",
                retryable=False,
            ) from exc

    def search_jobs(self, request: SearchJobsRequest) -> SearchJobsResult:
        normalized_query = _validate_non_empty("query", request.query)
        normalized_limit = _validate_limit(request.limit)
        normalized_location: str | None = None
        payload = {"query": normalized_query, "limit": normalized_limit}
        if request.location is not None:
            normalized_location = _validate_non_empty("location", request.location)
            payload["location"] = normalized_location

        if self._search_jobs_provider is None:
            self._raise_not_implemented("search_jobs", request=payload)

        try:
            return self._search_jobs_provider.search_jobs(
                SearchJobsRequest(
                    query=normalized_query,
                    location=normalized_location,
                    limit=normalized_limit,
                )
            )
        except OperationLookupError:
            raise
        except Exception as exc:
            raise OperationLookupError(
                "search_jobs",
                f"Public jobs search failed for query '{normalized_query}': {exc}",
                retryable=False,
            ) from exc

    def get_job_details(self, request: JobDetailsRequest) -> JobDetailsResult:
        normalized_job_id = _validate_non_empty("job_id", request.job_id)
        if self._job_details_provider is None:
            self._raise_not_implemented(
                "get_job_details",
                request={"job_id": normalized_job_id},
            )

        try:
            return self._job_details_provider.get_job_details(
                JobDetailsRequest(job_id=normalized_job_id)
            )
        except OperationLookupError:
            raise
        except Exception as exc:
            raise OperationLookupError(
                "get_job_details",
                f"Job details lookup failed for '{normalized_job_id}': {exc}",
                retryable=False,
            ) from exc

    def get_company_profile(self, request: CompanyProfileRequest) -> CompanyProfileResult:
        normalized_company_id = _validate_non_empty("company_id", request.company_id)
        if self._company_profile_provider is None:
            self._raise_not_implemented(
                "get_company_profile",
                request={"company_id": normalized_company_id},
            )
        try:
            return self._company_profile_provider.get_company_profile(
                CompanyProfileRequest(company_id=normalized_company_id)
            )
        except CompanyProfileLookupError:
            raise
        except Exception as exc:
            raise CompanyProfileLookupError(
                f"Company profile lookup failed for '{normalized_company_id}': {exc}",
                retryable=False,
            ) from exc

    def get_company_posts(self, request: CompanyPostsRequest) -> None:
        self._raise_not_implemented(
            "get_company_posts",
            request={
                "company_id": _validate_non_empty("company_id", request.company_id),
                "limit": _validate_limit(request.limit),
            },
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
