# linkedin-hybrid-mcp

`linkedin-hybrid-mcp` is a new Python MCP service intended to follow an API-first architecture for LinkedIn automation and data access.

Milestone 1 in this repository is intentionally limited to:

- Python project scaffolding
- architecture documentation
- a minimal MCP server skeleton
- basic `health` and `service_info` tools

It does **not** yet implement LinkedIn authentication, browser bootstrap, HTTP clients, or any reverse-engineered/private API behavior.

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
  server.py
docs/
  architecture.md
tests/
  test_server.py
```

## Available MCP tools

- `health`: basic service liveness metadata
- `service_info`: milestone and architecture summary

## Status

This repository is currently a scaffold for Milestone 1 only.



## Runtime note

The `mcp` runtime dependency is kept optional in Milestone 1 so the scaffold and tests remain runnable on machines that do not yet have a Python 3.10+ interpreter available.
