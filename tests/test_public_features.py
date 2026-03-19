from __future__ import annotations

import pytest

from linkedin_hybrid_mcp.domain import OperationLookupError
from linkedin_hybrid_mcp.domain import (
    JobDetailsRequest,
    PersonProfileRequest,
    SearchJobsRequest,
    SearchPeopleRequest,
)
from linkedin_hybrid_mcp.public_features import (
    DuckDuckGoLinkedInPeopleSearchProvider,
    LinkedInPublicJobDetailsProvider,
    LinkedInPublicJobsSearchProvider,
    LinkedInPublicPersonProfileProvider,
    parse_job_details_html,
    parse_job_search_html,
    parse_people_search_html,
    parse_person_profile_html,
)


def test_parse_people_search_html_extracts_linkedin_profile_hits() -> None:
    html = """
    <html><body>
      <a href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.linkedin.com%2Fin%2Falice-doe-123%2F">Alice</a>
      <a href="https://www.linkedin.com/in/bob-smith/">Bob</a>
    </body></html>
    """

    result = parse_people_search_html(query="alice", limit=2, html=html)

    assert result.source == "duckduckgo_site_search"
    assert len(result.hits) == 2
    assert result.hits[0].person_id == "alice-doe-123"
    assert result.hits[1].person_id == "bob-smith"


def test_parse_person_profile_html_extracts_person_fields() -> None:
    html = """
    <html><head>
      <meta property="og:title" content="Alice Doe - Staff Engineer | LinkedIn" />
      <meta property="og:url" content="https://www.linkedin.com/in/alice-doe/" />
      <meta property="og:description" content="Building reliable systems." />
      <script type="application/ld+json">{
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Alice Doe",
        "jobTitle": "Staff Engineer",
        "address": {"addressLocality": "Taipei"}
      }</script>
    </head></html>
    """

    profile = parse_person_profile_html(
        person_id="alice-doe",
        html=html,
        fetched_url="https://www.linkedin.com/in/alice-doe/",
    )

    assert profile.name == "Alice Doe"
    assert profile.headline == "Staff Engineer"
    assert profile.location == "Taipei"


def test_parse_person_profile_html_raises_when_name_missing() -> None:
    html = "<html><head><meta property='og:url' content='https://www.linkedin.com/in/x/' /></head></html>"

    with pytest.raises(OperationLookupError, match="parseable person name"):
        parse_person_profile_html(
            person_id="x",
            html=html,
            fetched_url="https://www.linkedin.com/in/x/",
        )


def test_parse_job_search_html_extracts_job_postings() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">[
        {
          "@type": "JobPosting",
          "identifier": {"value": "123"},
          "title": "Backend Engineer",
          "url": "https://www.linkedin.com/jobs/view/123/",
          "hiringOrganization": {"name": "Acme"},
          "jobLocation": {"address": {"addressLocality": "Taipei"}}
        }
      ]</script>
    </head></html>
    """

    result = parse_job_search_html(query="engineer", location="Taipei", limit=5, html=html)

    assert len(result.hits) == 1
    assert result.hits[0].job_id == "123"
    assert result.hits[0].company_name == "Acme"


def test_parse_job_details_html_extracts_job_fields() -> None:
    html = """
    <html><head>
      <meta property="og:url" content="https://www.linkedin.com/jobs/view/123/" />
      <script type="application/ld+json">{
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Backend Engineer",
        "description": "Build systems",
        "datePosted": "2026-03-01",
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"name": "Acme"},
        "jobLocation": {"address": {"addressLocality": "Taipei"}}
      }</script>
    </head></html>
    """

    details = parse_job_details_html(
        job_id="123",
        html=html,
        fetched_url="https://www.linkedin.com/jobs/view/123/",
    )

    assert details.title == "Backend Engineer"
    assert details.company_name == "Acme"
    assert details.date_posted == "2026-03-01"


def test_parse_job_details_html_raises_when_title_missing() -> None:
    with pytest.raises(OperationLookupError, match="parseable job title"):
        parse_job_details_html(
            job_id="123",
            html="<html><head></head></html>",
            fetched_url="https://www.linkedin.com/jobs/view/123/",
        )


def test_people_provider_builds_duckduckgo_url() -> None:
    calls: list[str] = []

    def fake_fetcher(url: str) -> str:
        calls.append(url)
        return "<html><a href='https://www.linkedin.com/in/alice-doe/'></a></html>"

    provider = DuckDuckGoLinkedInPeopleSearchProvider(text_fetcher=fake_fetcher)
    result = provider.search_people(request=SearchPeopleRequest(query="alice", limit=1))

    assert calls[0].startswith("https://duckduckgo.com/html/")
    assert result.hits[0].person_id == "alice-doe"


def test_person_profile_provider_builds_linkedin_url() -> None:
    calls: list[str] = []

    def fake_fetcher(url: str) -> str:
        calls.append(url)
        return """
        <html><head>
          <meta property='og:title' content='Alice Doe | LinkedIn' />
          <meta property='og:url' content='https://www.linkedin.com/in/alice-doe/' />
        </head></html>
        """

    provider = LinkedInPublicPersonProfileProvider(text_fetcher=fake_fetcher)
    profile = provider.get_person_profile(request=PersonProfileRequest(person_id="alice-doe"))

    assert calls == ["https://www.linkedin.com/in/alice-doe/"]
    assert profile.name == "Alice Doe"


def test_jobs_provider_builds_linkedin_search_url() -> None:
    calls: list[str] = []

    def fake_fetcher(url: str) -> str:
        calls.append(url)
        return "<html><a href='/jobs/view/123/'></a></html>"

    provider = LinkedInPublicJobsSearchProvider(text_fetcher=fake_fetcher)
    result = provider.search_jobs(
        request=SearchJobsRequest(query="engineer", location="Taipei", limit=1)
    )

    assert calls[0].startswith("https://www.linkedin.com/jobs/search/")
    assert result.hits[0].job_id == "123"


def test_job_details_provider_builds_linkedin_job_url() -> None:
    calls: list[str] = []

    def fake_fetcher(url: str) -> str:
        calls.append(url)
        return "<html><head><meta property='og:title' content='Backend Engineer | LinkedIn' /></head></html>"

    provider = LinkedInPublicJobDetailsProvider(text_fetcher=fake_fetcher)
    details = provider.get_job_details(request=JobDetailsRequest(job_id="123"))

    assert calls == ["https://www.linkedin.com/jobs/view/123/"]
    assert details.title == "Backend Engineer"
