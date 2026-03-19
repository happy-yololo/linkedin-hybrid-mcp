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

- [ ] Milestone 3 — Transport scaffold
  - typed transport errors
  - request settings / limits
  - retry/backoff policy
  - safe header handling
  - generic authenticated request scaffold
  - transport self-test helpers
  - status: implemented locally, not yet committed at the time this roadmap was added

- [ ] Milestone 4 — Safe MCP diagnostics tools
  - auth status tool
  - clear session tool
  - bootstrap/refresh placeholders surfaced safely
  - service diagnostics

- [ ] Milestone 5 — Security and documentation polish
  - storage/security notes
  - threat model
  - configuration documentation
  - runtime notes

- [ ] Milestone 6 — Feature parity roadmap
  - benchmark against `linkedin-mcp-server`
  - target tools:
    - `search_people`
    - `get_person_profile`
    - `search_jobs`
    - `get_job_details`
    - `get_company_profile`
    - `get_company_posts`
  - implement only when honestly supported and tested

## Working principles
- API-first, not browser-first
- browser only for auth bootstrap or recovery when necessary
- no fake LinkedIn endpoint claims
- tests should pass before each commit
- push each stable milestone to GitHub
