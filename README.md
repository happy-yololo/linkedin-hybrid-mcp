# linkedin-hybrid-mcp

`linkedin-hybrid-mcp` is a new Python MCP service intended to follow an API-first architecture for LinkedIn automation and data access.

Milestone 3 in this repository is intentionally limited to:

- Python project scaffolding
- architecture documentation
- a minimal MCP server skeleton
- basic `health` and `service_info` tools
- a local auth/session storage scaffold for future work
- a generic typed HTTP transport scaffold for future authenticated calls

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
tests/
  test_auth.py
  test_server.py
```

## Available MCP tools

- `health`: basic service liveness metadata
- `service_info`: milestone, architecture, and local auth scaffold summary

## Status

This repository currently includes a local-only auth/session scaffold:

- configurable local storage paths
- JSON-backed session metadata load/save helpers
- auth readiness status evaluation
- explicit placeholders for future browser bootstrap and refresh flows

The repository still does not implement real LinkedIn login or API calls.

## Transport scaffold status

The repository now includes a production-shaped but generic HTTP transport scaffold:

- typed transport errors
- request settings for timeouts and response size limits
- retry/backoff policy for retryable failures
- safe header validation and redacted diagnostics
- a generic authenticated request helper that requires explicit caller-supplied auth headers
- a transport self-test helper that reports readiness without making live network calls

This transport layer is intentionally generic. It does not claim to know or implement LinkedIn private endpoints, cookies, or request formats.

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
