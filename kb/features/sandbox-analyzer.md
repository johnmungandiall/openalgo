# Feature: Sandbox / Analyzer Mode

> "Analyze mode" routes all trading to an isolated paper-trading engine (₹1 Cr virtual capital) instead of the live broker. Fully separate `db/sandbox.db`.

## Toggle & routing
- Global flag `get_analyze_mode()` ([database/settings_db.py](../../database/settings_db.py)). Controls at `/sandbox`; request/response inspection at `/analyzer`.
- Bridge: [services/sandbox_service.py](../../services/sandbox_service.py) — `is_sandbox_mode()` ([:25](../../services/sandbox_service.py#L25)), `sandbox_place_order()` ([:40](../../services/sandbox_service.py#L40)). Each live service checks analyze mode and delegates here (see [[order-execution]]).

## Engine ([sandbox/](../../sandbox/))
- `ExecutionEngine` ([sandbox/execution_engine.py:36](../../sandbox/execution_engine.py#L36)): background loop (~5s) fetches live quotes via `services.quotes_service.get_quotes/get_multiquotes`, fills pending orders by price type (MARKET/LIMIT/SL/SL-M), enforces rate limits, creates trades/positions.
- Managers: `order_manager`, `position_manager`, `fund_manager` (margin/leverage), `holdings_manager`, `squareoff_manager`.
- Threads: `execution_thread.start_execution_engine()`, `squareoff_thread.start_squareoff_scheduler()` (exchange-aligned auto square-off), `catch_up_processor` / `catchup_missed_settlements` (T+1 settlement on restart). `websocket_execution_engine.py` = WS-driven variant.

## Persistence
[database/sandbox_db.py](../../database/sandbox_db.py): `SandboxOrders`, `SandboxPositions`, `SandboxTrades`. Isolated from live `openalgo.db`.

## Startup
Auto-started in [app.py:701-746](../../app.py#L701) when `get_analyze_mode()` is on (execution engine + square-off scheduler + settlement catch-up, in a thread pool).

## Events → UI
Engine emits `sandbox.order_filled` / `sandbox.auto_squareoff` / `sandbox.t1_settlement` (socketio-only) and `analyzer_update` → React sandbox UI auto-refresh. See [[order-execution]].
