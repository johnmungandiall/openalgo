# Feature: Order Execution & EventBus

> How an order flows API → service → broker, and how side-effects (logs, SocketIO, Telegram, WhatsApp) fan out via an in-process EventBus.

## Order flow
1. REST namespace [restx_api/place_order.py](../../restx_api/place_order.py) (or webhook/UI) → validates API key.
2. Service [services/place_order_service.py](../../services/place_order_service.py): `validate_order_data()` ([:65](../../services/place_order_service.py#L65)) checks `REQUIRED_ORDER_FIELDS`/`VALID_*` from [utils/constants.py](../../utils/constants.py).
3. Branch on **analyze mode** (`get_analyze_mode()`): live → real broker; analyze → sandbox engine (see [[sandbox-analyzer]]).
4. Live: `import_broker_module()` ([:26](../../services/place_order_service.py#L26)) → `broker.<name>.api.order_api.place_order(...)` with auth token from [database/auth_db.py](../../database/auth_db.py).
5. Publish an event (`OrderPlacedEvent` / `OrderFailedEvent` / `AnalyzerErrorEvent`).

## EventBus (decouples side-effects)
- [utils/event_bus.py](../../utils/event_bus.py): `EventBus` ([:25](../../utils/event_bus.py#L25)), `publish()` non-blocking via `ThreadPoolExecutor` ([:53](../../utils/event_bus.py#L53)), global singleton `bus` ([:70](../../utils/event_bus.py#L70)). `_safe_call` isolates subscriber errors.
- Events: [events/](../../events/) — `OrderEvent` base ([events/base.py:9](../../events/base.py#L9)) carries `mode`, `api_type`, `request_data`, `response_data`, `api_key`; topics in `order_events.py`, `position_events.py`, `batch_events.py`, `analyzer_events.py`, `sandbox_events.py`.
- Subscribers: [subscribers/](../../subscribers/) — `log`, `socketio`, `telegram`, `whatsapp`. Wired once at boot by `register_all()` ([subscribers/__init__.py:19](../../subscribers/__init__.py#L19), called [app.py:139](../../app.py#L139)).
- Topics: `order.placed/failed/no_action/modified/cancelled`, `orders.all_cancelled`, `position.closed`, `basket/split/options/multiorder.completed`, `analyzer.error`, `sandbox.*` (socketio-only, analyze mode).

## Order modes (Action Center)
Auto (direct execution) vs Semi-Auto (manual approval) — [services/action_center_service.py](../../services/action_center_service.py), [database/action_center_db.py](../../database/action_center_db.py).

## Order types/constants
Product `CNC/NRML/MIS`; price `MARKET/LIMIT/SL/SL-M`; action `BUY/SELL`. See [[conventions]].
