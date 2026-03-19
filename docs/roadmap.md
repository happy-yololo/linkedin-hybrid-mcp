# Roadmap

## Goal
Build `linkedin-hybrid-mcp` into an API-first, production-shaped MCP service for LinkedIn workflows.

## Milestones

- [x] Milestone 1 — Project scaffold
  - Python package layout
  - README
  - architecture notes
  - minimal MCP server skeleton
  - `health` and `service_info`
  - commit: `6589761`

- [x] Milestone 2 — Auth/session scaffold
  - storage path resolution
  - session metadata model
  - save/load/clear helpers
  - auth status evaluation
  - explicit placeholders for future bootstrap/refresh flows
  - commit: `8702e25`

- [x] Milestone 3 — Transport scaffold
  - typed transport errors
  - request settings / limits
  - retry/backoff policy
  - safe header handling
  - generic authenticated request scaffold
  - transport self-test helpers
  - commit: `6fd3025`

- [x] Milestone 4 — Safe MCP diagnostics tools
  - auth status tool
  - clear session tool
  - bootstrap/refresh placeholders surfaced safely
  - service diagnostics
  - commit: `eba9c79`

- [x] Milestone 5 — Security and documentation polish
  - storage/security notes
  - threat model
  - configuration documentation
  - runtime notes
  - docs aligned to current scaffold reality

- [x] Milestone 6 — Honest feature-parity scaffolding
  - benchmark against `linkedin-mcp-server`
  - target tools:
    - `search_people`
    - `get_person_profile`
    - `search_jobs`
    - `get_job_details`
    - `get_company_profile`
    - `get_company_posts`
  - typed placeholder domain/service layer added
  - safe `not_implemented` MCP tool payloads added
  - implement only when honestly supported and tested

- [x] Milestone 7 — First real feature phase (`get_company_profile`)
  - typed company profile result and provider interfaces
  - LinkedIn-backed public company page fetch + metadata parser
  - MCP payload supports implemented / lookup_failed / not_implemented states
  - opt-in flag: `LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC=1`
  - tests for parser, provider wiring, and server payload behavior

- [x] Milestone 8 — Public-web people/jobs/profile expansion
  - real opt-in providers for:
    - `search_people` (public web indexing path)
    - `get_person_profile` (public LinkedIn profile metadata parser)
    - `search_jobs` (public LinkedIn jobs search parser)
    - `get_job_details` (public LinkedIn job page metadata parser)
  - MCP payloads now report:
    - `implemented`
    - `lookup_failed`
    - `not_implemented`
  - `get_company_posts` remains blocked with typed payload blockers, attempted URL targets, and required capabilities

## Working principles
- API-first, not browser-first
- browser only for auth bootstrap or recovery when necessary
- no fake LinkedIn endpoint claims
- no fake LinkedIn private API integration
- no pretend scraping support
- tests should pass before each commit
- push each stable milestone to GitHub
