# Feature: Broker Integration (33 brokers)

> Pluggable broker layer. Each [broker/<name>/](../../broker/) is self-contained and loaded dynamically by name; nothing hard-codes broker classes.

## Standard plugin structure (e.g. [broker/zerodha/](../../broker/zerodha/))
- `api/auth_api.py` — `authenticate_broker()` (OAuth2 / API-key / TOTP login)
- `api/order_api.py` — place/modify/cancel; `api/data.py` — quotes/depth/history; `api/funds.py`, `api/margin_api.py`, optional `api/gtt_api.py`
- `mapping/` — OpenAlgo ↔ broker symbol/order/transform mapping
- `streaming/<name>_adapter.py` + `_websocket.py` — real-time feed. See [[websocket-streaming]]
- `database/master_contract_db.py` — downloads symbol master → `SymToken` table
- `plugin.json` — metadata + capabilities

## Loading (lazy, by name)
- [utils/plugin_loader.py:65](../../utils/plugin_loader.py#L65) `load_broker_auth_functions()` returns `_LazyBrokerAuthDict` ([:83](../../utils/plugin_loader.py#L83)) — imports a broker's `auth_api` only on first `<broker>_auth` access (avoids ~3.5s import of 30+ SDKs at boot).
- [utils/plugin_loader.py:17](../../utils/plugin_loader.py#L17) `load_broker_capabilities()` caches all `plugin.json` (`supported_exchanges`, `broker_type`, `leverage_config`) in memory; surfaced to frontend route guards.
- Services import order/data modules dynamically: `import_broker_module()` → `broker.<name>.api.order_api` ([services/place_order_service.py:26](../../services/place_order_service.py#L26)).

## plugin.json fields ([broker/zerodha/plugin.json](../../broker/zerodha/plugin.json))
`supported_exchanges[]`, `broker_type` (`IN_stock`/`crypto`), `leverage_config` (bool). Brokers without `supported_exchanges` are skipped by the capability loader.

## Adding a broker
1. `broker/<name>/` with `api/ mapping/ database/ streaming/`  2. `plugin.json`  3. add to `VALID_BROKERS` in `.env`  4. restart.

## Gotchas (broker quote/funds APIs lie — verify per broker)
- Quote "modes" differ: not every broker returns OI/volume/depth in REST. If REST can't, build OI from the snap-quote WS feed so `get_multiquotes` returns real `oi` (else option chain is empty — consumers skip `oi<=0`).
- Funds endpoints may return `m2mrealized`/`m2munrealized` as null/0; derive M2M from the positions feed. See root CLAUDE.md "Quotes/Funds" sections.

Reference impls: zerodha, dhan, angel. Symbol format + `SymToken` schema: [[conventions]].
