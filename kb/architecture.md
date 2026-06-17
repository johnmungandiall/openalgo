# Architecture

> Module map + data flow. Two areas: Python Flask backend (root) and React SPA ([frontend/](../frontend/)). See [[subprojects/backend]], [[subprojects/frontend]].

## Backend module map (root)
| Dir | Responsibility |
| --- | --- |
| [app.py](../app.py) | Flask factory, blueprint registration, middleware order, schedulers, WS-proxy launch |
| [blueprints/](../blueprints/) | 49 UI/webhook route handlers (server-rendered + React serving + webhooks) |
| [restx_api/](../restx_api/) | `/api/v1/` REST namespaces (50+), API-key auth. See [[features/api-layer]] |
| [services/](../services/) | Business logic (68 files). One `*_service.py` per API/feature |
| [broker/](../broker/) | 33 broker plugins. See [[features/broker-integration]] |
| [database/](../database/) | SQLAlchemy models + `init_db` per DB; caches; token storage |
| [websocket_proxy/](../websocket_proxy/) | Unified WS server (8765) + ZeroMQ bus. See [[features/websocket-streaming]] |
| [sandbox/](../sandbox/) | Analyze-mode trading engine. See [[features/sandbox-analyzer]] |
| [events/](../events/) + [subscribers/](../subscribers/) | In-process EventBus. See [[features/order-execution]] |
| [utils/](../utils/) | logging, plugin_loader, event_bus, security/traffic middleware, httpx pool, version |
| [mcp/](../mcp/) | stdio MCP server. See [[features/mcp]] |

## Request pipeline (middleware wraps in reverse; last registered = outermost)
`TrafficLogger → Security(IP ban) → CSP → Flask(routing,CSRF,session) → API-key auth (/api/v1) → service → broker`
Registered [app.py:248-251](../app.py#L248) (security first, then traffic outermost). `/api/v1` is CSRF-exempt ([app.py:245](../app.py#L245)).

## Startup sequence
1. `create_app()` — socketio, EventBus subscribers ([app.py:139](../app.py#L139)), CSRF, limiter, CORS, CSP, register blueprints ([app.py:236-297](../app.py#L236)).
2. `setup_environment()` — lazy-load broker plugins; spawn **background thread** that inits all DBs in parallel then schedulers ([app.py:599-670](../app.py#L599)). `app.db_ready` Event gates requests ([app.py:421](../app.py#L421)).
3. WS proxy: child **process** under eventlet, OS **thread** on dev server ([app.py:873-889](../app.py#L873)).
4. Per-request cleanup: `teardown_appcontext` removes ~22 scoped sessions ([app.py:828](../app.py#L828)).

## Databases (6, isolated — NullPool, never StaticPool)
`db/openalgo.db` (main), `logs.db`, `latency.db`, `health.db`, `sandbox.db`, `historify.duckdb`. Each has its own `init_db` in [database/](../database/).

## Real-time channels
- Flask-SocketIO events (`order_update`, `analyzer_update`, `cache_loaded`) → React live UI (via subscribers).
- WS proxy (8765) for market data; ZeroMQ PUB/SUB (5555) internal bus + cache invalidation.

## Runtime constraint
Prod = gunicorn + **eventlet, -w 1**. No `asyncio.run()` (monkey-patched); run async on a real OS thread. Dev server uses plain threading. See [[conventions]].
