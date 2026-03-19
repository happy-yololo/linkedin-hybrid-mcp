from __future__ import annotations

import pytest

from linkedin_hybrid_mcp.domain import (
    DomainOperationNotImplementedError,
    FEATURE_BENCHMARK,
    CompanyPostsRequest,
    CompanyProfileRequest,
    JobDetailsRequest,
    LinkedInFeatureParityService,
    PersonProfileRequest,
    SearchJobsRequest,
    SearchPeopleRequest,
    benchmark_operations,
)


def test_benchmark_operations_match_expected_surface() -> None:
    assert benchmark_operations() == [
        "search_people",
        "get_person_profile",
        "search_jobs",
        "get_job_details",
        "get_company_profile",
        "get_company_posts",
    ]


def test_placeholder_metadata_is_safe_and_explicit() -> None:
    service = LinkedInFeatureParityService()

    payload = service.placeholder_for("search_people", request={"query": "alice"}).to_dict()

    assert payload["benchmark"] == FEATURE_BENCHMARK
    assert payload["implemented"] is False
    assert payload["status"] == "not_implemented"
    assert "private API" in payload["notes"][1]


@pytest.mark.parametrize(
    ("payload_request", "method_name", "operation_name"),
    [
        (SearchPeopleRequest(query="alice"), "search_people", "search_people"),
        (PersonProfileRequest(person_id="person-1"), "get_person_profile", "get_person_profile"),
        (SearchJobsRequest(query="engineer", location="Taipei"), "search_jobs", "search_jobs"),
        (JobDetailsRequest(job_id="job-1"), "get_job_details", "get_job_details"),
        (CompanyProfileRequest(company_id="company-1"), "get_company_profile", "get_company_profile"),
        (CompanyPostsRequest(company_id="company-1"), "get_company_posts", "get_company_posts"),
    ],
)
def test_placeholder_operations_raise_explicit_not_implemented(
    payload_request: object,
    method_name: str,
    operation_name: str,
) -> None:
    service = LinkedInFeatureParityService()

    with pytest.raises(DomainOperationNotImplementedError, match=operation_name):
        getattr(service, method_name)(payload_request)


def test_search_people_rejects_empty_query() -> None:
    service = LinkedInFeatureParityService()

    with pytest.raises(ValueError, match="query must not be empty"):
        service.search_people(SearchPeopleRequest(query=""))
