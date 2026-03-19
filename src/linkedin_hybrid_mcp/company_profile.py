"""LinkedIn-backed company profile integration via public company pages."""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from linkedin_hybrid_mcp.domain import (
    CompanyProfileLookupError,
    CompanyProfileRequest,
    CompanyProfileResult,
)

DEFAULT_USER_AGENT = "linkedin-hybrid-mcp/0.1.0"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024


class TextFetcher(Protocol):
    """Boundary abstraction for loading remote HTML text."""

    def __call__(self, url: str) -> str:
        """Fetch text content from a URL."""


def _extract_meta_content(html: str, key: str) -> str | None:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]*content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']{re.escape(key)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]*content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']{re.escape(key)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return unescape(match.group(1)).strip()
    return None


def _extract_ld_json_blocks(html: str) -> list[object]:
    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parsed: list[object] = []
    for block in blocks:
        text = block.strip()
        if not text:
            continue
        try:
            parsed.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    return parsed


def _iter_json_objects(value: object):
    if isinstance(value, dict):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _find_organization_object(html: str) -> dict[str, object] | None:
    for block in _extract_ld_json_blocks(html):
        for obj in _iter_json_objects(block):
            raw_type = obj.get("@type")
            if isinstance(raw_type, str) and raw_type.lower() == "organization":
                return obj
            if isinstance(raw_type, list) and any(
                isinstance(item, str) and item.lower() == "organization" for item in raw_type
            ):
                return obj
    return None


def parse_company_profile_html(*, company_id: str, html: str, fetched_url: str) -> CompanyProfileResult:
    """Parse a LinkedIn company page HTML payload into typed profile data."""

    org = _find_organization_object(html)
    canonical_url = _extract_meta_content(html, "og:url") or fetched_url
    name = _extract_meta_content(html, "og:title")
    description = _extract_meta_content(html, "og:description")
    logo_url = _extract_meta_content(html, "og:image")

    website: str | None = None
    industry: str | None = None

    if org is not None:
        if not name:
            raw_name = org.get("name")
            if isinstance(raw_name, str):
                name = raw_name.strip()

        raw_desc = org.get("description")
        if isinstance(raw_desc, str) and not description:
            description = raw_desc.strip()

        raw_url = org.get("url")
        if isinstance(raw_url, str) and raw_url.strip():
            canonical_url = raw_url.strip()

        raw_logo = org.get("logo")
        if isinstance(raw_logo, str) and raw_logo.strip() and not logo_url:
            logo_url = raw_logo.strip()

        raw_website = org.get("sameAs")
        if isinstance(raw_website, list):
            for candidate in raw_website:
                if isinstance(candidate, str) and "linkedin.com" not in candidate.lower():
                    website = candidate.strip()
                    break

        raw_industry = org.get("industry")
        if isinstance(raw_industry, str) and raw_industry.strip():
            industry = raw_industry.strip()

    if not name:
        raise CompanyProfileLookupError(
            "LinkedIn company page did not contain a parseable company name.",
            retryable=False,
        )

    return CompanyProfileResult(
        company_id=company_id,
        canonical_url=canonical_url,
        name=name,
        description=description,
        website=website,
        industry=industry,
        logo_url=logo_url,
        source="linkedin_public_company_page",
        notes=(
            "Data is parsed from public LinkedIn company page metadata (Open Graph and JSON-LD).",
            "Some fields may be missing depending on LinkedIn page content and localization.",
        ),
    )


def default_text_fetcher(url: str) -> str:
    """Load an HTML document with conservative request defaults."""

    request = Request(
        url=url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            body = response.read(DEFAULT_MAX_RESPONSE_BYTES + 1)
            if len(body) > DEFAULT_MAX_RESPONSE_BYTES:
                raise CompanyProfileLookupError(
                    "LinkedIn company page response exceeded max size guardrail.",
                    retryable=False,
                )
            return body.decode("utf-8", errors="replace")
    except HTTPError as exc:
        retryable = exc.code in {429, 500, 502, 503, 504}
        raise CompanyProfileLookupError(
            f"LinkedIn company page request failed with status {exc.code}.",
            retryable=retryable,
        ) from exc
    except URLError as exc:
        raise CompanyProfileLookupError(
            f"LinkedIn company page request failed before response: {exc.reason}",
            retryable=True,
        ) from exc


def _build_company_page_url(company_id: str) -> str:
    company_id = company_id.strip()
    if not company_id:
        raise ValueError("company_id must not be empty.")
    if company_id.startswith("http://") or company_id.startswith("https://"):
        return company_id
    return f"https://www.linkedin.com/company/{company_id}/"


class LinkedInPublicCompanyProfileProvider:
    """Company profile provider using LinkedIn public company pages."""

    def __init__(self, *, text_fetcher: TextFetcher | None = None) -> None:
        self._text_fetcher = text_fetcher or default_text_fetcher

    def get_company_profile(self, request: CompanyProfileRequest) -> CompanyProfileResult:
        target_url = _build_company_page_url(request.company_id)
        html = self._text_fetcher(target_url)
        return parse_company_profile_html(
            company_id=request.company_id,
            html=html,
            fetched_url=target_url,
        )
