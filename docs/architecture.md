# Architecture Overview

## Objective

Build a maintainable MCP service for LinkedIn workflows with an API-first execution model instead of a browser-heavy scraping architecture.

## Milestone 1 scope

This milestone only establishes the skeleton:

- package and repository structure
- MCP server entrypoint
- initial tools for health and service metadata
- architecture notes for future milestones

The following are intentionally not implemented yet:

- LinkedIn authentication bootstrap
- session persistence
- authenticated HTTP clients
- API adapters
- browser automation fallback flows
- domain tools for profile, messaging, search, or feed operations

## Planned architecture

### 1. Auth bootstrap layer

Purpose:
Acquire authenticated state with the minimum browser usage necessary.

Expected direction:

- use a browser only to complete login and any anti-bot or MFA steps
- extract the authenticated artifacts required for follow-on HTTP requests
- persist session state in a controlled local store

This layer is only conceptual in Milestone 1.

### 2. API transport layer

Purpose:
Execute the default runtime path through authenticated HTTP requests.

Expected responsibilities:

- session-aware request execution
- rate limit handling
- retry and backoff policy
- response normalization
- transport-level observability

This layer is not implemented in Milestone 1.

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

Milestone 1 ships only:

- `health`
- `service_info`

Future milestones can add LinkedIn-specific tools after auth and transport layers exist.

## Engineering principles

- API-first by default
- browser usage minimized and isolated
- explicit boundaries between auth, transport, and tool layers
- honest documentation about unsupported features
- incremental milestones with small atomic changes

