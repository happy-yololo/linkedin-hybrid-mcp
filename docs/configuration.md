# Configuration

## Python version

- local development target: Python 3.9+
- optional MCP runtime dependency: install the `mcp` extra on Python 3.10+

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Optional runtime dependency:

```bash
pip install -e .[mcp]
```

## Environment variables

### `LINKEDIN_HYBRID_MCP_HOME`

If set, this becomes the root directory for local scaffold state.

Example:

```bash
export LINKEDIN_HYBRID_MCP_HOME="$PWD/.local-state"
```

### `XDG_DATA_HOME`

If `LINKEDIN_HYBRID_MCP_HOME` is not set, the service uses:

```text
$XDG_DATA_HOME/linkedin-hybrid-mcp
```

### Default location

If neither variable is set, the service uses:

```text
~/.local/share/linkedin-hybrid-mcp
```

## Stored files

The current scaffold writes only one file:

- `session.json`: local session metadata scaffold

This file is not a working LinkedIn login cache. It is only a placeholder for future authenticated flows.

## Runtime notes

- importing and testing the package does not require the `mcp` dependency
- diagnostics tools do not make live network calls
- the generic transport layer requires explicit caller-supplied auth headers for any authenticated request
