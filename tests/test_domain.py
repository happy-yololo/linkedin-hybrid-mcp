from __future__ import annotations

import pytest

from linkedin_hybrid_mcp.domain import (
    CompanyPostsRequest,
    CompanyProfileRequest,
    DomainOperationNotImplementedError,
    FEATURE_BENCHMARK,
    JobDetailsResult,
    JobSearchHit,
    JobDetailsRequest,
    LinkedInFeatureParityService,
    PersonProfileResult,
    PersonSearchHit,
    PersonProfileRequest,
    SearchJobsResult,
    SearchJobsRequest,
    SearchPeopleResult,
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


def test_service_returns_results_when_public_providers_are_configured() -> None:
    class FakePeopleProvider:
        def search_people(self, _request: SearchPeopleRequest) -> SearchPeopleResult:
            return SearchPeopleResult(
                query="alice",
                limit=1,
                hits=(
                    PersonSearchHit(
                        person_id="alice",
                        profile_url="https://www.linkedin.com/in/alice/",
                        name="Alice",
                    ),
                ),
                source="fake",
            )

    class FakePersonProvider:
        def get_person_profile(self, _request: PersonProfileRequest) -> PersonProfileResult:
            return PersonProfileResult(
                person_id="alice",
                canonical_url="https://www.linkedin.com/in/alice/",
                name="Alice",
            )

    class FakeJobsProvider:
        def search_jobs(self, _request: SearchJobsRequest) -> SearchJobsResult:
            return SearchJobsResult(
                query="engineer",
                location="Taipei",
                limit=1,
                hits=(
                    JobSearchHit(
                        job_id="123",
                        job_url="https://www.linkedin.com/jobs/view/123/",
                        title="Engineer",
                    ),
                ),
                source="fake",
            )

    class FakeJobDetailsProvider:
        def get_job_details(self, _request: JobDetailsRequest) -> JobDetailsResult:
            return JobDetailsResult(
                job_id="123",
                job_url="https://www.linkedin.com/jobs/view/123/",
                title="Engineer",
            )

    service = LinkedInFeatureParityService(
        search_people_provider=FakePeopleProvider(),
        person_profile_provider=FakePersonProvider(),
        search_jobs_provider=FakeJobsProvider(),
        job_details_provider=FakeJobDetailsProvider(),
    )

    people = service.search_people(SearchPeopleRequest(query="alice"))
    person = service.get_person_profile(PersonProfileRequest(person_id="alice"))
    jobs = service.search_jobs(SearchJobsRequest(query="engineer", location="Taipei"))
    job_details = service.get_job_details(JobDetailsRequest(job_id="123"))

    assert people.hits[0].person_id == "alice"
    assert person.name == "Alice"
    assert jobs.hits[0].job_id == "123"
    assert job_details.title == "Engineer"
