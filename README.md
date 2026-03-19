# linkedin-hybrid-mcp

`linkedin-hybrid-mcp` is a Python MCP service scaffold for LinkedIn workflows with an API-first design target.

Milestone 8 in this repository currently includes:

- Python project scaffolding
- architecture, roadmap, security, and configuration documentation
- a minimal MCP server skeleton with safe diagnostics tools
- a local auth/session storage scaffold for future work
- a generic typed HTTP transport scaffold for future authenticated calls
- typed benchmark interfaces for LinkedIn domain operations
- opt-in public-web providers for selected benchmark operations

It does **not** yet implement working LinkedIn authentication, browser bootstrap, LinkedIn-specific HTTP clients, or any reverse-engineered/private API behavior.

## Design direction

The intended design is inspired by the cleaner separation used by API-first projects such as `notebooklm-py`:

- browser use only where necessary to bootstrap authenticated state
- authenticated HTTP/API calls for the normal execution path
- browser fallback reserved for flows that cannot be completed through stable API calls

That design is documented here as a target architecture, not as a completed implementation.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
# Optional when running the real MCP server on Python 3.10+: pip install -e .[mcp]
linkedin-hybrid-mcp
```

## Project layout

```text
src/linkedin_hybrid_mcp/
  __init__.py
  __main__.py
  auth.py
  client.py
  config.py
  server.py
docs/
  architecture.md
  configuration.md
  roadmap.md
  security.md
tests/
  test_auth.py
  test_client.py
  test_domain.py
  test_server.py
```

## Available MCP tools

- `health`: basic service liveness metadata
- `service_info`: milestone, architecture, and local auth scaffold summary
- `auth_status_tool`: local session readiness without network access
- `transport_self_test_tool`: transport readiness without network access
- `clear_session_tool`: remove local session scaffold state
- `auth_flow_placeholders`: explicit not-implemented auth entry points
- `service_diagnostics`: combined safe diagnostics snapshot
- `feature_parity_status`: benchmark tracking for implemented vs blocked operations
- `get_company_profile`: opt-in LinkedIn-backed implementation using public company page metadata parsing (`LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC=1`)
- `search_people`, `get_person_profile`, `search_jobs`, `get_job_details`: opt-in public-web implementations (`LINKEDIN_HYBRID_ENABLE_PUBLIC_WEB=1`)
- `get_company_posts`: explicit blocked payload with typed blocker codes, attempted public URLs, and next honest steps

## Status

This repository currently includes a local-only auth/session scaffold:

- configurable local storage paths
- JSON-backed session metadata load/save helpers
- auth readiness status evaluation
- explicit placeholders for future browser bootstrap and refresh flows

The repository still does not implement real LinkedIn login or API calls.

## Feature parity scaffold status

This repository tracks a narrow benchmark set from `linkedin-mcp-server`:

- `search_people`
- `get_person_profile`
- `search_jobs`
- `get_job_details`
- `get_company_profile`
- `get_company_posts`

`get_company_profile` has a real opt-in implementation path that:

- resolves a LinkedIn company page URL from `company_id`
- fetches the public company page over HTTP
- parses Open Graph and JSON-LD metadata into typed output

`search_people`, `get_person_profile`, `search_jobs`, and `get_job_details` now have real opt-in public-web implementations that:

- use public-page/public-search fetches only
- parse public HTML metadata into typed result payloads
- return `lookup_failed` when integrations are enabled but runtime fetch/parse fails

Limitations and blockers:

- coverage depends on LinkedIn public page metadata availability and shape
- no browser automation fallback is implemented yet
- no LinkedIn private API integration is implemented
- `search_people` relies on public web indexing coverage (DuckDuckGo HTML endpoint), not LinkedIn private APIs
- `get_company_posts` remains blocked: company feed pages are dynamic and do not provide a stable public metadata list equivalent to other implemented operations
- blocker output now includes:
  - `blockers` with stable `code` values and supporting evidence
  - `attempted_public_urls` for reproducible public-web probe targets
  - `required_next_capabilities` and `next_honest_steps` to unblock in a future milestone

## Transport scaffold status

The repository now includes a production-shaped but generic HTTP transport scaffold:

- typed transport errors
- request settings for timeouts and response size limits
- retry/backoff policy for retryable failures
- safe header validation and redacted diagnostics
- a generic authenticated request helper that requires explicit caller-supplied auth headers
- a transport self-test helper that reports readiness without making live network calls

This transport layer is intentionally generic. It does not claim to know or implement LinkedIn private endpoints, cookies, or request formats.

## Feature flags

- `LINKEDIN_HYBRID_ENABLE_PUBLIC_WEB=1`: enables `search_people`, `get_person_profile`, `search_jobs`, `get_job_details`
- `LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC=1`: enables `get_company_profile`

## Security and configuration docs

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Configuration](docs/configuration.md)
- [Security notes](docs/security.md)

## Local auth storage

By default the session scaffold stores metadata at:

```text
~/.local/share/linkedin-hybrid-mcp/session.json
```

You can override the storage root with:

- `LINKEDIN_HYBRID_MCP_HOME=/custom/path`
- `XDG_DATA_HOME=/custom/xdg-root`

The stored file is intended for local development scaffolding only. It does not claim to provide a working LinkedIn authenticated session.

## Runtime note

The `mcp` runtime dependency is kept optional so the scaffold and tests remain runnable on machines that do not yet have a Python 3.10+ interpreter available.
