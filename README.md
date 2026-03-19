# linkedin-hybrid-mcp

`linkedin-hybrid-mcp` is a Python MCP service scaffold for LinkedIn workflows with an API-first design target.

Milestone 6 in this repository currently includes:

- Python project scaffolding
- architecture, roadmap, security, and configuration documentation
- a minimal MCP server skeleton with safe diagnostics tools
- a local auth/session storage scaffold for future work
- a generic typed HTTP transport scaffold for future authenticated calls
- typed placeholder interfaces for benchmarked LinkedIn domain operations

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
- `feature_parity_status`: benchmark tracking for unimplemented LinkedIn operations
- `search_people`, `get_person_profile`, `search_jobs`, `get_job_details`, `get_company_profile`, `get_company_posts`: safe placeholder tools that return clear non-implementation payloads

## Status

This repository currently includes a local-only auth/session scaffold:

- configurable local storage paths
- JSON-backed session metadata load/save helpers
- auth readiness status evaluation
- explicit placeholders for future browser bootstrap and refresh flows

The repository still does not implement real LinkedIn login or API calls.

## Feature parity scaffold status

This repository now tracks a narrow benchmark set from `linkedin-mcp-server`:

- `search_people`
- `get_person_profile`
- `search_jobs`
- `get_job_details`
- `get_company_profile`
- `get_company_posts`

These operations are intentionally placeholders only. They fail closed with explicit `not_implemented` payloads and do not perform network access, scraping, or private API calls.

## Transport scaffold status

The repository now includes a production-shaped but generic HTTP transport scaffold:

- typed transport errors
- request settings for timeouts and response size limits
- retry/backoff policy for retryable failures
- safe header validation and redacted diagnostics
- a generic authenticated request helper that requires explicit caller-supplied auth headers
- a transport self-test helper that reports readiness without making live network calls

This transport layer is intentionally generic. It does not claim to know or implement LinkedIn private endpoints, cookies, or request formats.

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
