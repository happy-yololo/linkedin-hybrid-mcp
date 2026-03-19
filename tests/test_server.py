from __future__ import annotations

from linkedin_hybrid_mcp.auth import SessionMetadata, save_session
from linkedin_hybrid_mcp.domain import (
    CompanyProfileLookupError,
    CompanyProfileRequest,
    CompanyProfileResult,
    JobDetailsRequest,
    JobDetailsResult,
    JobSearchHit,
    LinkedInFeatureParityService,
    OperationLookupError,
    PersonProfileRequest,
    PersonProfileResult,
    PersonSearchHit,
    SearchJobsRequest,
    SearchJobsResult,
    SearchPeopleRequest,
    SearchPeopleResult,
)
from linkedin_hybrid_mcp.config import resolve_storage_paths
from linkedin_hybrid_mcp.server import (
    auth_flow_placeholders_payload,
    auth_status_payload,
    clear_session_payload,
    feature_parity_payload,
    get_company_posts_payload,
    get_company_profile_payload,
    get_job_details_payload,
    get_person_profile_payload,
    health_payload,
    search_jobs_payload,
    search_people_payload,
    service_diagnostics_payload,
    service_info_payload,
    transport_diagnostics_payload,
)


def test_health_payload() -> None:
    payload = health_payload()

    assert payload["status"] == "ok"
    assert payload["service"] == "linkedin-hybrid-mcp"


def test_service_info_payload_marks_scaffold() -> None:
    payload = service_info_payload()

    assert payload["milestone"] == "milestone-8"
    assert payload["architecture"]["mode"] == "api-first"
    assert payload["architecture"]["implemented"] == "partial"
    assert payload["auth"]["implemented"] == "local session scaffold only"
    assert payload["transport"]["implemented"] == "generic authenticated request scaffold only"
    assert (
        payload["feature_parity"]["implemented"]
        == "placeholder domain/service layer only (public-web integrations are opt-in)"
    )


def test_auth_status_payload_reports_local_readiness(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = auth_status_payload(paths=paths)

    assert payload["auth"]["state"] == "missing"
    assert "local session metadata readiness only" in payload["notes"][0]


def test_transport_diagnostics_payload_stays_non_network(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = transport_diagnostics_payload(paths=paths)

    assert payload["transport"]["auth"]["state"] == "missing"
    assert payload["runtime"]["tool_wrapper_mode"] in {"fastmcp", "import-only"}
    assert "does not make live network calls" in payload["notes"][0]


def test_clear_session_payload_reports_before_and_after(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})
    save_session(
        SessionMetadata(login_state="bootstrapped", cookies_present=True, headers_present=True),
        paths,
    )

    payload = clear_session_payload(paths=paths)

    assert payload["cleared"] is True
    assert payload["auth_before"]["state"] == "ready"
    assert payload["auth_after"]["state"] == "missing"
    assert paths.session_file.exists() is False


def test_auth_flow_placeholders_payload_surfaces_stub_messages(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = auth_flow_placeholders_payload(paths=paths)

    assert payload["bootstrap"]["implemented"] is False
    assert payload["bootstrap"]["status"] == "not_implemented"
    assert "Browser bootstrap is not implemented" in payload["bootstrap"]["message"]
    assert "Session refresh is not implemented" in payload["refresh"]["message"]


def test_service_diagnostics_payload_combines_subpayloads(tmp_path) -> None:
    paths = resolve_storage_paths(env={"LINKEDIN_HYBRID_MCP_HOME": str(tmp_path / "state")})

    payload = service_diagnostics_payload(paths=paths)

    assert payload["milestone"] == "milestone-8"
    assert payload["auth_status"]["auth"]["state"] == "missing"
    assert payload["transport_self_test"]["transport"]["auth"]["state"] == "missing"
    assert payload["auth_placeholders"]["bootstrap"]["implemented"] is False
    assert payload["feature_parity"]["implemented"] is False


def test_feature_parity_payload_lists_benchmarked_operations() -> None:
    payload = feature_parity_payload()

    assert payload["milestone"] == "milestone-8"
    assert payload["implemented"] is False
    assert payload["implemented_operations"] == []
    assert "get_company_profile" in payload["placeholder_operations"]
    assert "search_people" in payload["operations"]


def test_feature_parity_payload_reflects_opt_in_flags(monkeypatch) -> None:
    monkeypatch.setenv("LINKEDIN_HYBRID_ENABLE_PUBLIC_WEB", "1")
    monkeypatch.setenv("LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC", "1")

    payload = feature_parity_payload()

    assert payload["implemented"] is True
    assert "search_people" in payload["implemented_operations"]
    assert "get_company_profile" in payload["implemented_operations"]
    assert "get_company_posts" in payload["placeholder_operations"]


def test_search_people_payload_fails_safely() -> None:
    payload = search_people_payload(query="alice", limit=5)

    assert payload["feature"]["status"] == "not_implemented"
    assert payload["feature"]["operation"] == "search_people"
    assert payload["feature"]["request"]["limit"] == 5


def test_get_person_profile_payload_fails_safely() -> None:
    payload = get_person_profile_payload(person_id="person-1")

    assert payload["feature"]["status"] == "not_implemented"
    assert payload["feature"]["operation"] == "get_person_profile"


def test_search_jobs_payload_fails_safely() -> None:
    payload = search_jobs_payload(query="engineer", location="Taipei", limit=3)

    assert payload["feature"]["status"] == "not_implemented"
    assert payload["feature"]["operation"] == "search_jobs"
    assert payload["feature"]["request"]["location"] == "Taipei"


def test_get_job_details_payload_fails_safely() -> None:
    payload = get_job_details_payload(job_id="job-1")

    assert payload["feature"]["status"] == "not_implemented"
    assert payload["feature"]["operation"] == "get_job_details"


def test_get_company_profile_payload_fails_safely() -> None:
    payload = get_company_profile_payload(company_id="company-1")

    assert payload["feature"]["status"] == "not_implemented"
    assert payload["feature"]["operation"] == "get_company_profile"


def test_get_company_profile_payload_returns_real_data_when_provider_is_wired(monkeypatch) -> None:
    class FakeProvider:
        def get_company_profile(self, request: CompanyProfileRequest) -> CompanyProfileResult:
            return CompanyProfileResult(
                company_id=request.company_id,
                canonical_url="https://www.linkedin.com/company/acme/",
                name="Acme Corp",
            )

    monkeypatch.setattr(
        "linkedin_hybrid_mcp.server.feature_parity_service",
        LinkedInFeatureParityService(company_profile_provider=FakeProvider()),
    )

    payload = get_company_profile_payload(company_id="acme")

    assert payload["feature"]["implemented"] is True
    assert payload["feature"]["status"] == "implemented"
    assert payload["company_profile"]["name"] == "Acme Corp"


def test_get_company_profile_payload_surfaces_lookup_failure(monkeypatch) -> None:
    class FakeProvider:
        def get_company_profile(self, request: CompanyProfileRequest) -> CompanyProfileResult:
            raise CompanyProfileLookupError("temporary failure", retryable=True)

    monkeypatch.setattr(
        "linkedin_hybrid_mcp.server.feature_parity_service",
        LinkedInFeatureParityService(company_profile_provider=FakeProvider()),
    )

    payload = get_company_profile_payload(company_id="acme")

    assert payload["feature"]["implemented"] is True
    assert payload["feature"]["status"] == "lookup_failed"
    assert payload["feature"]["retryable"] is True


def test_search_people_payload_returns_real_data_when_provider_is_wired(monkeypatch) -> None:
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

    monkeypatch.setattr(
        "linkedin_hybrid_mcp.server.feature_parity_service",
        LinkedInFeatureParityService(search_people_provider=FakePeopleProvider()),
    )

    payload = search_people_payload(query="alice", limit=1)

    assert payload["feature"]["status"] == "implemented"
    assert payload["people_search"]["hits"][0]["person_id"] == "alice"


def test_search_people_payload_surfaces_lookup_failure(monkeypatch) -> None:
    class FailingPeopleProvider:
        def search_people(self, _request: SearchPeopleRequest) -> SearchPeopleResult:
            raise OperationLookupError("search_people", "temporary failure", retryable=True)

    monkeypatch.setattr(
        "linkedin_hybrid_mcp.server.feature_parity_service",
        LinkedInFeatureParityService(search_people_provider=FailingPeopleProvider()),
    )

    payload = search_people_payload(query="alice", limit=1)

    assert payload["feature"]["status"] == "lookup_failed"
    assert payload["feature"]["retryable"] is True


def test_get_person_profile_payload_returns_real_data_when_provider_is_wired(monkeypatch) -> None:
    class FakePersonProvider:
        def get_person_profile(self, _request: PersonProfileRequest) -> PersonProfileResult:
            return PersonProfileResult(
                person_id="alice",
                canonical_url="https://www.linkedin.com/in/alice/",
                name="Alice",
            )

    monkeypatch.setattr(
        "linkedin_hybrid_mcp.server.feature_parity_service",
        LinkedInFeatureParityService(person_profile_provider=FakePersonProvider()),
    )

    payload = get_person_profile_payload(person_id="alice")

    assert payload["feature"]["status"] == "implemented"
    assert payload["person_profile"]["name"] == "Alice"


def test_search_jobs_payload_returns_real_data_when_provider_is_wired(monkeypatch) -> None:
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

    monkeypatch.setattr(
        "linkedin_hybrid_mcp.server.feature_parity_service",
        LinkedInFeatureParityService(search_jobs_provider=FakeJobsProvider()),
    )

    payload = search_jobs_payload(query="engineer", location="Taipei", limit=1)

    assert payload["feature"]["status"] == "implemented"
    assert payload["jobs_search"]["hits"][0]["job_id"] == "123"


def test_get_job_details_payload_returns_real_data_when_provider_is_wired(monkeypatch) -> None:
    class FakeJobDetailsProvider:
        def get_job_details(self, _request: JobDetailsRequest) -> JobDetailsResult:
            return JobDetailsResult(
                job_id="123",
                job_url="https://www.linkedin.com/jobs/view/123/",
                title="Engineer",
            )

    monkeypatch.setattr(
        "linkedin_hybrid_mcp.server.feature_parity_service",
        LinkedInFeatureParityService(job_details_provider=FakeJobDetailsProvider()),
    )

    payload = get_job_details_payload(job_id="123")

    assert payload["feature"]["status"] == "implemented"
    assert payload["job_details"]["title"] == "Engineer"


def test_get_company_posts_payload_fails_safely() -> None:
    payload = get_company_posts_payload(company_id="company-1", limit=2)

    assert payload["feature"]["status"] == "not_implemented"
    assert payload["feature"]["operation"] == "get_company_posts"
    assert payload["feature"]["request"]["limit"] == 2
    assert payload["feature"]["blockers"]
