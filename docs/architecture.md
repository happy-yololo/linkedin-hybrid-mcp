# Architecture Overview

## Objective

Build a maintainable MCP service for LinkedIn workflows with an API-first execution model instead of a browser-heavy scraping architecture.

## Current scope

Milestone 8 establishes the current runtime skeleton plus local auth/session persistence primitives, a generic transport layer, safe diagnostics tooling, and first real public-web feature integrations:

- package and repository structure
- MCP server entrypoint
- initial tools for health and service metadata
- local session metadata model
- local JSON storage helpers
- auth readiness/status evaluation
- typed generic HTTP transport scaffolding
- retry/backoff and request guardrails
- non-network transport self-test diagnostics
- LinkedIn public company profile metadata parser/provider (`get_company_profile`, opt-in)
- public-web providers for `search_people`, `get_person_profile`, `search_jobs`, `get_job_details` (opt-in)
- architecture notes for future milestones
- security and configuration documentation

The following are intentionally not implemented yet:

- LinkedIn authentication bootstrap
- LinkedIn-specific authenticated HTTP clients
- API adapters
- browser automation fallback flows
- implemented `get_company_posts`

## Planned architecture

### 1. Auth bootstrap layer

Purpose:
Acquire authenticated state with the minimum browser usage necessary.

Current implementation:

- local storage path resolution for persisted auth/session state
- JSON-backed session metadata file management
- status evaluation for missing, incomplete, expired, or ready session state
- explicit placeholders for future bootstrap and refresh flows

Expected future direction:

- use a browser only to complete login and any anti-bot or MFA steps
- extract the authenticated artifacts required for follow-on HTTP requests
- persist session state in a controlled local store

This layer is only partially implemented in Milestone 2. It does not perform LinkedIn login.

### 2. API transport layer

Purpose:
Execute the default runtime path through authenticated HTTP requests.

Expected responsibilities:

- session-aware request execution
- rate limit handling
- retry and backoff policy
- response normalization
- transport-level observability

Current implementation:

- generic absolute-URL request builder
- request settings for timeout and response size limits
- typed transport errors
- retry/backoff for retryable status codes and timeout failures
- safe header validation and redacted diagnostics
- generic authenticated request execution that requires caller-supplied auth headers
- transport self-test helpers that avoid live network calls

Non-goals in the current scaffold:

- no LinkedIn endpoint discovery
- no fake or inferred private API support
- no persistence of raw cookie/header secrets in the current session model

This layer is only partially implemented. It provides transport primitives, not a LinkedIn API client.

### 3. Browser fallback layer

Purpose:
Handle edge cases where API-first execution is insufficient.

Expected use cases:

- auth/bootstrap only
- flows blocked by anti-automation or missing API coverage
- resilience fallback for brittle edge paths

The browser should not be the default path for ordinary operations.

### 4. MCP tool layer

Purpose:
Expose stable, well-scoped tools to MCP clients while hiding auth and transport complexity.

Milestone 2 ships only:

- `health`
- `service_info`

Milestone 4 ships:

- `health`
- `service_info`
- `auth_status_tool`
- `transport_self_test_tool`
- `clear_session_tool`
- `auth_flow_placeholders`
- `service_diagnostics`

Milestone 8 includes benchmark tools for:

- `search_people`
- `get_person_profile`
- `search_jobs`
- `get_job_details`
- `get_company_profile` (real when `LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC=1`)
- `get_company_posts`

`search_people`, `get_person_profile`, `search_jobs`, and `get_job_details` can execute real public-web HTTP+parsing flows when `LINKEDIN_HYBRID_ENABLE_PUBLIC_WEB=1`.

`get_company_profile` can execute a real HTTP+parsing flow against LinkedIn public company pages when `LINKEDIN_HYBRID_ENABLE_COMPANY_PROFILE_PUBLIC=1`.

`get_company_posts` remains intentionally unimplemented with explicit typed blockers surfaced in tool payloads:

- blocker codes and evidence for why public static parsing is not reliable
- attempted public URL targets used for honest probe scope
- required capabilities/next steps for a future browser/auth or verified-public-source implementation

## Engineering principles

- API-first by default
- browser usage minimized and isolated
- explicit boundaries between auth, transport, and tool layers
- honest documentation about unsupported features
- incremental milestones with small atomic changes
