from __future__ import annotations

import pytest

from linkedin_hybrid_mcp.company_profile import (
    LinkedInPublicCompanyProfileProvider,
    parse_company_profile_html,
)
from linkedin_hybrid_mcp.domain import (
    CompanyProfileLookupError,
    CompanyProfileRequest,
    LinkedInFeatureParityService,
)


def test_parse_company_profile_html_extracts_org_and_meta_fields() -> None:
    html = """
    <html>
      <head>
        <meta property=\"og:title\" content=\"Acme Corp\" />
        <meta property=\"og:url\" content=\"https://www.linkedin.com/company/acme/\" />
        <meta property=\"og:description\" content=\"Builds reliable systems.\" />
        <meta property=\"og:image\" content=\"https://cdn.example.com/acme.png\" />
        <script type=\"application/ld+json\">{
          \"@context\": \"https://schema.org\",
          \"@type\": \"Organization\",
          \"name\": \"Acme Corporation\",
          \"industry\": \"Software Development\",
          \"sameAs\": [\"https://www.linkedin.com/company/acme/\", \"https://acme.example.com\"]
        }</script>
      </head>
      <body></body>
    </html>
    """

    profile = parse_company_profile_html(
        company_id="acme",
        html=html,
        fetched_url="https://www.linkedin.com/company/acme/",
    )

    assert profile.company_id == "acme"
    assert profile.name == "Acme Corp"
    assert profile.canonical_url == "https://www.linkedin.com/company/acme/"
    assert profile.description == "Builds reliable systems."
    assert profile.website == "https://acme.example.com"
    assert profile.industry == "Software Development"


def test_parse_company_profile_html_raises_when_name_missing() -> None:
    html = "<html><head><meta property='og:url' content='https://www.linkedin.com/company/acme/' /></head></html>"

    with pytest.raises(CompanyProfileLookupError, match="parseable company name"):
        parse_company_profile_html(
            company_id="acme",
            html=html,
            fetched_url="https://www.linkedin.com/company/acme/",
        )


def test_public_provider_builds_linkedin_company_url() -> None:
    calls: list[str] = []

    def fake_fetcher(url: str) -> str:
        calls.append(url)
        return """
        <html><head>
          <meta property=\"og:title\" content=\"Acme Corp\" />
          <meta property=\"og:url\" content=\"https://www.linkedin.com/company/acme/\" />
        </head></html>
        """

    provider = LinkedInPublicCompanyProfileProvider(text_fetcher=fake_fetcher)

    profile = provider.get_company_profile(CompanyProfileRequest(company_id="acme"))

    assert calls == ["https://www.linkedin.com/company/acme/"]
    assert profile.name == "Acme Corp"


def test_service_returns_company_profile_when_provider_is_configured() -> None:
    def fake_fetcher(_url: str) -> str:
        return """
        <html><head>
          <meta property=\"og:title\" content=\"Acme Corp\" />
          <meta property=\"og:url\" content=\"https://www.linkedin.com/company/acme/\" />
        </head></html>
        """

    provider = LinkedInPublicCompanyProfileProvider(text_fetcher=fake_fetcher)
    service = LinkedInFeatureParityService(company_profile_provider=provider)

    result = service.get_company_profile(CompanyProfileRequest(company_id="acme"))

    assert result.company_id == "acme"
    assert result.name == "Acme Corp"
