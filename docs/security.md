# Security Notes

## Current security posture

`linkedin-hybrid-mcp` is still a local scaffold. It does not perform real LinkedIn authentication, does not call LinkedIn endpoints, and does not ship browser automation or scraping support.

The security goal for the current milestone is narrower:

- keep the local auth/session scaffold explicit
- avoid claiming secret handling that does not exist
- avoid network activity in diagnostics paths
- document the trust boundaries before feature work expands

## Local storage model

The repository currently persists only local session metadata in JSON:

- default path: `~/.local/share/linkedin-hybrid-mcp/session.json`
- override with `LINKEDIN_HYBRID_MCP_HOME`
- fallback override with `XDG_DATA_HOME`

The stored metadata is intentionally limited to scaffold state such as:

- account identifier
- login state
- expiration timestamp
- booleans describing whether cookies or headers are present
- optional browser profile path
- local notes

Current non-goals:

- no encrypted secret store
- no keychain integration
- no remote token exchange
- no persistence of raw LinkedIn cookies or authorization headers by the scaffold itself

## Threat model

### Assets

- local session metadata file
- any future caller-supplied auth headers passed into the transport layer
- local browser profile path references
- MCP diagnostic payloads

### Trust boundaries

- local filesystem boundary around the configured storage root
- MCP client boundary around exposed tool payloads
- future network boundary for authenticated transport calls

### Expected threats

- accidental disclosure of local session metadata from weak filesystem permissions
- accidental logging of auth headers or cookies
- unsafe header injection into outgoing requests
- over-claiming support for LinkedIn auth or private API behavior
- future misuse of diagnostics tools as a substitute for real auth validation

### Mitigations already present

- diagnostics tools are non-network and descriptive only
- request diagnostics redact sensitive headers such as `Authorization` and `Cookie`
- request builder rejects unsafe headers such as `Host` and `Content-Length`
- authenticated transport requires explicit caller-supplied auth headers and a ready local session state
- placeholder auth flows fail closed with `not implemented` errors

### Residual risks

- the JSON session file is plaintext metadata on disk
- the scaffold does not yet enforce restrictive file permissions
- future integrations could widen the threat surface if they start persisting secrets
- MCP clients still need to treat tool outputs as potentially sensitive local state

## Hard rules for future implementation

- do not add fake LinkedIn private API support
- do not add pretend scraping support
- do not silently persist raw cookies or tokens without an explicit storage design
- keep diagnostics redacted and non-network by default
- prefer short-lived in-memory secret handling wherever possible
