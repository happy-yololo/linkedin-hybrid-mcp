"""Public-web LinkedIn feature providers for people and jobs operations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from linkedin_hybrid_mcp.domain import (
    JobDetailsRequest,
    JobDetailsResult,
    JobSearchHit,
    OperationLookupError,
    PersonProfileRequest,
    PersonProfileResult,
    PersonSearchHit,
    SearchJobsRequest,
    SearchJobsResult,
    SearchPeopleRequest,
    SearchPeopleResult,
)

DEFAULT_USER_AGENT = "linkedin-hybrid-mcp/0.1.0"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024


class TextFetcher(Protocol):
    """Boundary abstraction for loading remote HTML text."""

    def __call__(self, url: str) -> str:
        """Fetch text content from a URL."""


@dataclass(frozen=True)
class PublicSearchRequest:
    """A normalized public-search request."""

    query: str
    limit: int


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
                raise OperationLookupError(
                    "public_fetch",
                    "Public web response exceeded max size guardrail.",
                    retryable=False,
                )
            return body.decode("utf-8", errors="replace")
    except HTTPError as exc:
        retryable = exc.code in {429, 500, 502, 503, 504}
        raise OperationLookupError(
            "public_fetch",
            f"Public web request failed with status {exc.code}.",
            retryable=retryable,
        ) from exc
    except URLError as exc:
        raise OperationLookupError(
            "public_fetch",
            f"Public web request failed before response: {exc.reason}",
            retryable=True,
        ) from exc


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


def _object_has_type(obj: dict[str, object], expected_type: str) -> bool:
    raw_type = obj.get("@type")
    if isinstance(raw_type, str):
        return raw_type.lower() == expected_type.lower()
    if isinstance(raw_type, list):
        return any(isinstance(item, str) and item.lower() == expected_type.lower() for item in raw_type)
    return False


def _find_json_objects_by_type(html: str, expected_type: str) -> list[dict[str, object]]:
    objects: list[dict[str, object]] = []
    for block in _extract_ld_json_blocks(html):
        for obj in _iter_json_objects(block):
            if _object_has_type(obj, expected_type):
                objects.append(obj)
    return objects


def _safe_slug_to_name(slug: str) -> str:
    cleaned = re.sub(r"[-_]+", " ", slug).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return slug
    return " ".join(part.capitalize() for part in cleaned.split(" "))


def _extract_linkedin_profile_urls_from_search_html(html: str) -> list[str]:
    urls: list[str] = []

    for match in re.findall(r"https?://[^\s\"'<>]+", html):
        candidate = unescape(match)
        parsed = urlparse(candidate)

        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            redirect_target = parse_qs(parsed.query).get("uddg")
            if redirect_target:
                candidate = unquote(redirect_target[0])
                parsed = urlparse(candidate)

        if "linkedin.com" not in parsed.netloc.lower() or "/in/" not in parsed.path:
            continue

        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized.endswith("/") is False:
            normalized = normalized + "/"
        urls.append(normalized)

    unique_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
    return unique_urls


def parse_people_search_html(*, query: str, limit: int, html: str) -> SearchPeopleResult:
    """Parse a public search HTML page into person profile hits."""

    hits: list[PersonSearchHit] = []
    for url in _extract_linkedin_profile_urls_from_search_html(html):
        match = re.search(r"/in/([^/?#]+)/?", url)
        if not match:
            continue
        slug = match.group(1).strip()
        if not slug:
            continue
        hits.append(
            PersonSearchHit(
                person_id=slug,
                profile_url=url,
                name=_safe_slug_to_name(slug),
                source="duckduckgo_site_search",
            )
        )
        if len(hits) >= limit:
            break

    return SearchPeopleResult(
        query=query,
        limit=limit,
        hits=tuple(hits),
        source="duckduckgo_site_search",
        notes=(
            "Search uses public web indexing (DuckDuckGo HTML) with site filters, not LinkedIn private APIs.",
            "Result names are inferred from profile URL slugs when richer metadata is unavailable.",
        ),
    )


def _build_people_search_url(query: str) -> str:
    return f"https://duckduckgo.com/html/?q={quote_plus(f'site:linkedin.com/in {query}')}&kp=-2"


def _build_person_profile_url(person_id: str) -> str:
    person_id = person_id.strip()
    if person_id.startswith("http://") or person_id.startswith("https://"):
        return person_id
    return f"https://www.linkedin.com/in/{person_id}/"


def _parse_title_into_name_headline(title: str | None) -> tuple[str | None, str | None]:
    if not title:
        return (None, None)

    title_without_brand = title.split("|")[0].strip()
    if " - " in title_without_brand:
        name, headline = title_without_brand.split(" - ", 1)
        return (name.strip() or None, headline.strip() or None)
    return (title_without_brand or None, None)


def parse_person_profile_html(*, person_id: str, html: str, fetched_url: str) -> PersonProfileResult:
    """Parse a LinkedIn person profile page HTML payload."""

    person_objects = _find_json_objects_by_type(html, "Person")
    og_title = _extract_meta_content(html, "og:title")
    inferred_name, inferred_headline = _parse_title_into_name_headline(og_title)

    name = inferred_name
    headline = inferred_headline
    about = _extract_meta_content(html, "og:description")
    profile_image_url = _extract_meta_content(html, "og:image")
    canonical_url = _extract_meta_content(html, "og:url") or fetched_url
    location: str | None = None

    for obj in person_objects:
        if not name and isinstance(obj.get("name"), str):
            name = obj["name"].strip()  # type: ignore[index]
        if isinstance(obj.get("jobTitle"), str) and not headline:
            headline = obj["jobTitle"].strip()  # type: ignore[index]
        if isinstance(obj.get("description"), str) and not about:
            about = obj["description"].strip()  # type: ignore[index]
        if isinstance(obj.get("url"), str):
            candidate_url = obj["url"].strip()  # type: ignore[index]
            if candidate_url:
                canonical_url = candidate_url
        if isinstance(obj.get("image"), str) and not profile_image_url:
            profile_image_url = obj["image"].strip()  # type: ignore[index]

        raw_address = obj.get("address")
        if isinstance(raw_address, dict):
            locality = raw_address.get("addressLocality")
            if isinstance(locality, str) and locality.strip():
                location = locality.strip()

    if not name:
        raise OperationLookupError(
            "get_person_profile",
            "LinkedIn public profile page did not contain a parseable person name.",
            retryable=False,
        )

    return PersonProfileResult(
        person_id=person_id,
        canonical_url=canonical_url,
        name=name,
        headline=headline,
        about=about,
        location=location,
        profile_image_url=profile_image_url,
        source="linkedin_public_profile_page",
        notes=(
            "Data is parsed from public LinkedIn profile metadata (Open Graph and JSON-LD Person).",
            "Profiles with limited public visibility may return partial fields.",
        ),
    )


def _extract_job_id_from_url(url: str) -> str | None:
    match = re.search(r"/jobs/view/(\d+)", url)
    if match:
        return match.group(1)
    return None


def _build_job_search_url(query: str, location: str | None) -> str:
    params: dict[str, str] = {"keywords": query}
    if location:
        params["location"] = location
    return f"https://www.linkedin.com/jobs/search/?{urlencode(params)}"


def _build_job_details_url(job_id: str) -> str:
    job_id = job_id.strip()
    if job_id.startswith("http://") or job_id.startswith("https://"):
        return job_id
    return f"https://www.linkedin.com/jobs/view/{job_id}/"


def _job_location_from_object(obj: dict[str, object]) -> str | None:
    raw_location = obj.get("jobLocation")
    if isinstance(raw_location, dict):
        raw_address = raw_location.get("address")
        if isinstance(raw_address, dict):
            locality = raw_address.get("addressLocality")
            if isinstance(locality, str) and locality.strip():
                return locality.strip()
    if isinstance(raw_location, list):
        for item in raw_location:
            if not isinstance(item, dict):
                continue
            raw_address = item.get("address")
            if isinstance(raw_address, dict):
                locality = raw_address.get("addressLocality")
                if isinstance(locality, str) and locality.strip():
                    return locality.strip()
    return None


def parse_job_search_html(*, query: str, location: str | None, limit: int, html: str) -> SearchJobsResult:
    """Parse LinkedIn public jobs-search HTML into job hits."""

    hits: list[JobSearchHit] = []
    seen_ids: set[str] = set()

    for obj in _find_json_objects_by_type(html, "JobPosting"):
        title = obj.get("title") if isinstance(obj.get("title"), str) else None
        url = obj.get("url") if isinstance(obj.get("url"), str) else None

        job_id: str | None = None
        raw_identifier = obj.get("identifier")
        if isinstance(raw_identifier, dict):
            raw_value = raw_identifier.get("value")
            if isinstance(raw_value, str) and raw_value.strip():
                job_id = raw_value.strip()

        if not job_id and isinstance(url, str):
            job_id = _extract_job_id_from_url(url)

        if not job_id or job_id in seen_ids:
            continue

        company_name: str | None = None
        raw_company = obj.get("hiringOrganization")
        if isinstance(raw_company, dict):
            raw_name = raw_company.get("name")
            if isinstance(raw_name, str) and raw_name.strip():
                company_name = raw_name.strip()

        job_url = url or f"https://www.linkedin.com/jobs/view/{job_id}/"
        hits.append(
            JobSearchHit(
                job_id=job_id,
                job_url=job_url,
                title=title.strip() if isinstance(title, str) else None,
                company_name=company_name,
                location=_job_location_from_object(obj),
                source="linkedin_public_jobs_search",
            )
        )
        seen_ids.add(job_id)
        if len(hits) >= limit:
            break

    if not hits:
        for relative_or_absolute in re.findall(r"(?:https?://www\.linkedin\.com)?/jobs/view/\d+/?", html):
            url = relative_or_absolute
            if url.startswith("/"):
                url = f"https://www.linkedin.com{url}"
            job_id = _extract_job_id_from_url(url)
            if not job_id or job_id in seen_ids:
                continue
            hits.append(JobSearchHit(job_id=job_id, job_url=url, source="linkedin_public_jobs_search"))
            seen_ids.add(job_id)
            if len(hits) >= limit:
                break

    return SearchJobsResult(
        query=query,
        location=location,
        limit=limit,
        hits=tuple(hits),
        source="linkedin_public_jobs_search",
        notes=(
            "Results are parsed from publicly accessible LinkedIn jobs search HTML.",
            "Coverage varies based on LinkedIn rendering and geo/language differences.",
        ),
    )


def parse_job_details_html(*, job_id: str, html: str, fetched_url: str) -> JobDetailsResult:
    """Parse a LinkedIn public job page HTML payload."""

    postings = _find_json_objects_by_type(html, "JobPosting")
    posting = postings[0] if postings else None

    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    description: str | None = None
    date_posted: str | None = None
    employment_type: str | None = None
    canonical_url = _extract_meta_content(html, "og:url") or fetched_url

    if posting is not None:
        raw_title = posting.get("title")
        if isinstance(raw_title, str) and raw_title.strip():
            title = raw_title.strip()

        raw_description = posting.get("description")
        if isinstance(raw_description, str) and raw_description.strip():
            description = raw_description.strip()

        raw_date_posted = posting.get("datePosted")
        if isinstance(raw_date_posted, str) and raw_date_posted.strip():
            date_posted = raw_date_posted.strip()

        raw_employment_type = posting.get("employmentType")
        if isinstance(raw_employment_type, str) and raw_employment_type.strip():
            employment_type = raw_employment_type.strip()

        raw_company = posting.get("hiringOrganization")
        if isinstance(raw_company, dict):
            raw_company_name = raw_company.get("name")
            if isinstance(raw_company_name, str) and raw_company_name.strip():
                company_name = raw_company_name.strip()

        location = _job_location_from_object(posting)

        raw_url = posting.get("url")
        if isinstance(raw_url, str) and raw_url.strip():
            canonical_url = raw_url.strip()

    if not title:
        og_title = _extract_meta_content(html, "og:title")
        if og_title:
            title = og_title.split("|")[0].strip()

    if not title:
        raise OperationLookupError(
            "get_job_details",
            "LinkedIn public job page did not contain a parseable job title.",
            retryable=False,
        )

    return JobDetailsResult(
        job_id=job_id,
        job_url=canonical_url,
        title=title,
        company_name=company_name,
        location=location,
        description=description,
        date_posted=date_posted,
        employment_type=employment_type,
        source="linkedin_public_job_page",
        notes=(
            "Data is parsed from public LinkedIn job page metadata (Open Graph and JSON-LD JobPosting).",
            "Some fields may be absent depending on LinkedIn page shape and availability.",
        ),
    )


class DuckDuckGoLinkedInPeopleSearchProvider:
    """People search via public web indexing (DuckDuckGo HTML endpoint)."""

    def __init__(self, *, text_fetcher: TextFetcher | None = None) -> None:
        self._text_fetcher = text_fetcher or default_text_fetcher

    def search_people(self, request: SearchPeopleRequest) -> SearchPeopleResult:
        target_url = _build_people_search_url(request.query)
        html = self._text_fetcher(target_url)
        return parse_people_search_html(query=request.query, limit=request.limit, html=html)


class LinkedInPublicPersonProfileProvider:
    """Person profile provider using public LinkedIn profile page metadata."""

    def __init__(self, *, text_fetcher: TextFetcher | None = None) -> None:
        self._text_fetcher = text_fetcher or default_text_fetcher

    def get_person_profile(self, request: PersonProfileRequest) -> PersonProfileResult:
        target_url = _build_person_profile_url(request.person_id)
        html = self._text_fetcher(target_url)
        return parse_person_profile_html(person_id=request.person_id, html=html, fetched_url=target_url)


class LinkedInPublicJobsSearchProvider:
    """Jobs search provider using LinkedIn public jobs search page metadata."""

    def __init__(self, *, text_fetcher: TextFetcher | None = None) -> None:
        self._text_fetcher = text_fetcher or default_text_fetcher

    def search_jobs(self, request: SearchJobsRequest) -> SearchJobsResult:
        target_url = _build_job_search_url(request.query, request.location)
        html = self._text_fetcher(target_url)
        return parse_job_search_html(
            query=request.query,
            location=request.location,
            limit=request.limit,
            html=html,
        )


class LinkedInPublicJobDetailsProvider:
    """Job details provider using public LinkedIn job page metadata."""

    def __init__(self, *, text_fetcher: TextFetcher | None = None) -> None:
        self._text_fetcher = text_fetcher or default_text_fetcher

    def get_job_details(self, request: JobDetailsRequest) -> JobDetailsResult:
        target_url = _build_job_details_url(request.job_id)
        html = self._text_fetcher(target_url)
        return parse_job_details_html(job_id=request.job_id, html=html, fetched_url=target_url)
