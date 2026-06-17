# Conventions

> Naming, patterns, and gotchas that filenames don't reveal. Verify constants in [utils/constants.py](../../utils/constants.py).

## Backend patterns
- **Layering**: route (`blueprints/`|`restx_api/`) → `services/<name>_service.py` → `broker/<name>/api/*` → `database/`. Don't call broker modules from routes directly.
- **Dynamic broker dispatch**: never hard-code a broker; import by name (`broker.<name>.api.<mod>`) — see [[broker-integration]].
- **DB access**: SQLAlchemy ORM only, **never raw SQL**. Each DB module owns a `scoped_session` (`db_session`) that MUST be added to the `teardown_appcontext` cleanup list ([app.py:834-857](../../app.py#L834)) or FDs leak.
- **SQLite pooling**: `NullPool` everywhere — **never `StaticPool`** (corrupts cursor under concurrency).
- **Logging**: `from utils.logging import get_logger; logger = get_logger(__name__)`. Errors: `logger.exception(...)` (auto-captures traceback → `log/errors.jsonl`). **Never** `import traceback`/`print_exc`. Read `log/errors.jsonl` first when debugging.
- **HTTP to brokers**: shared httpx HTTP/2 client via [utils/httpx_client.py](../../utils/httpx_client.py) (connection pooling).
- **Events over direct calls** for side-effects: publish to `bus` ([utils/event_bus.py](../../utils/event_bus.py)), don't call telegram/socketio inline. See [[order-execution]].
- **eventlet/prod**: no `asyncio.run()` / `async-await` (monkey-patched, `-w 1`); run async on a real OS thread. Code must also work on the threaded dev server.

## Order/symbol constants ([utils/constants.py](../../utils/constants.py))
- Product `CNC/NRML/MIS` ([:74](../../utils/constants.py#L74)); price `MARKET/LIMIT/SL/SL-M` ([:82](../../utils/constants.py#L82)); action `BUY/SELL` ([:88](../../utils/constants.py#L88)).
- Required order fields [:109](../../utils/constants.py#L109). Use set members (`FNO_EXCHANGES`, `CRYPTO_EXCHANGES`) not literals.
- **Symbol format** (OpenAlgo-normalized, mapped per broker in `broker/*/mapping/`, stored in `SymToken`):
  - Equity `INFY`; Future `BANKNIFTY24APR24FUT`; Option `NIFTY28MAR2420800CE`.
  - `SymToken` cols: `symbol` (OpenAlgo) / `brsymbol` (broker) / `exchange` / `brexchange` / `token` / `expiry` / `strike` / `lotsize` / `instrumenttype` / `tick_size`.

## Style
- Python: Ruff (line 100, py312, rules E/F/W/I/B/C4/UP). 4-space indent, Google docstrings, imports stdlib→third-party→local.
- React/TS: Biome (`frontend/biome.json`), functional components + hooks, PascalCase files, TanStack Query for server state + Zustand for client state.
- Commits: Conventional Commits (`feat:`/`fix:`/`docs:`/`refactor:`).

## Versioning (two independent)
Platform = [utils/version.py](../../utils/version.py) + `pyproject.toml:4` + `uv sync`. SDK pin = `openalgo==X` in `pyproject.toml`/`requirements*.txt`. See root CLAUDE.md.
