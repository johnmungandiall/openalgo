# Feature: Strategy Hosts (Python / Flow / Webhook / Chartink)

> Four ways to automate trades on top of the unified API. All ultimately call the order services in [[order-execution]].

## 1. Python Strategy Host (`/python`)
- [blueprints/python_strategy.py](../../blueprints/python_strategy.py) (`url_prefix="/python"`). Each strategy runs in its own **subprocess** (`subprocess.Popen`, `RUNNING_STRATEGIES` map [:61](../../blueprints/python_strategy.py#L61), platform-specific args [:331](../../blueprints/python_strategy.py#L331)).
- Scheduled on IST times via **APScheduler** (`init_python_strategy()` from [app.py:651](../../app.py#L651)). Logs stream to UI via SocketIO. Metadata in [database/strategy_db.py](../../database/strategy_db.py). Scripts live in `strategies/`.

## 2. Flow — no-code builder (`/flow`)
- [blueprints/flow.py](../../blueprints/flow.py) (`url_prefix="/flow"`, [:17](../../blueprints/flow.py#L17)). Definitions as JSON in [database/flow_db.py](../../database/flow_db.py). Frontend canvas uses `@xyflow/react` ([frontend/src/pages/flow/FlowEditor.tsx](../../frontend/src/pages/flow/FlowEditor.tsx)).
- Runtime: [services/flow_executor_service.py](../../services/flow_executor_service.py) interprets node graph; `flow_price_monitor_service.py` watches prices; `flow_scheduler_service.py` (APScheduler) for triggers. `execute_workflow_now()` [:303](../../blueprints/flow.py#L303).
- Webhook triggers: `trigger_webhook(token)` [:600](../../blueprints/flow.py#L600), `trigger_webhook_with_symbol` [:614](../../blueprints/flow.py#L614) (CSRF-exempt, [app.py:389](../../app.py#L389)).

## 3. Webhook Strategies (`/strategy`)
- [blueprints/strategy.py](../../blueprints/strategy.py) (`url_prefix="/strategy"`, [:56](../../blueprints/strategy.py#L56)). Per-strategy `webhook_id` (UUID); endpoint `POST /strategy/webhook/<webhook_id>` [:869](../../blueprints/strategy.py#L869) (CSRF-exempt). For TradingView/Amibroker/Excel signals. Persisted in [database/strategy_db.py](../../database/strategy_db.py).

## 4. Chartink (`/chartink`)
- [blueprints/chartink.py](../../blueprints/chartink.py) + [database/chartink_db.py](../../database/chartink_db.py). Scanner-alert webhook (CSRF-exempt, [app.py:387](../../app.py#L387)).

Shared APScheduler instance across Flow/Historify/Python hosts. Schedulers start in the app.py background init thread (after DB tables exist).
