# Feature: MCP Integration

> Two MCP surfaces: a local stdio server, and an opt-in remote HTTP+OAuth transport. Let LLM clients (Claude Desktop/Cursor/Windsurf, claude.ai) drive OpenAlgo.

## Local stdio MCP (default, not network-exposed)
- [mcp/mcpserver.py](../../mcp/mcpserver.py) — runs over stdio with a desktop MCP client. Tool registry: [utils/mcp_tool_registry.py](../../utils/mcp_tool_registry.py). Tools map to `/api/v1` operations.

## Remote MCP (opt-in, OFF by default)
- Enabled only when `MCP_HTTP_ENABLED=true`. Gated in [app.py:302-382](../../app.py#L302):
  - **Refuses** to start if `FLASK_DEBUG` is on (debug tracebacks leak bearer tokens).
  - **Requires** `MCP_PUBLIC_URL` (anchors JWT iss/aud; without it tokens become portable across instances).
  - Sets `OPENALGO_MCP_HTTP_BOOT=1` before importing the HTTP blueprint.
- Blueprints: [blueprints/mcp_http.py](../../blueprints/mcp_http.py) (JSON-RPC dispatch + SSE transport), [blueprints/mcp_oauth.py](../../blueprints/mcp_oauth.py) (OAuth2 authorize/token/revoke + DCR + `.well-known`).
- OAuth state: [database/oauth_db.py](../../database/oauth_db.py); signing key via [utils/oauth_keys.py](../../utils/oauth_keys.py) `ensure_signing_key()`; tokens/codes in `utils/oauth_tokens.py`/`oauth_codes.py`.
- CSRF-exempt endpoints: token, revoke, register_client, mcp_dispatch, mcp_sse ([app.py:355-365](../../app.py#L355)) — they use Bearer / client_secret+PKCE, not session cookies. `/oauth/authorize` POST is **not** exempt (browser consent form).
- Boot warnings if `write:orders` scope or DCR auto-approval are on ([app.py:370-378](../../app.py#L370)).

## Frontend admin
`/admin/remote-mcp` ([frontend/src/pages/admin/RemoteMcp.tsx](../../frontend/src/pages/admin/RemoteMcp.tsx)).

See `docs/prd/remote-mcp.md` for the security design.
