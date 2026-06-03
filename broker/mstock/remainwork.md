# MStock Broker Integration — Status

All core modules are implemented. The integration supports authentication,
order management, positions/holdings, quotes, multi-quotes, historical data,
market depth, funds, and real-time streaming.

## Files

- `broker/mstock/api/__init__.py` — ✅
- `broker/mstock/api/auth_api.py` — ✅
- `broker/mstock/api/order_api.py` — ✅
- `broker/mstock/api/data.py` — ✅
- `broker/mstock/api/funds.py` — ✅
- `broker/mstock/api/margin_api.py` — ✅
- `broker/mstock/api/mstockwebsocket.py` — ✅ (sync `websocket-client`; eventlet-safe)
- `broker/mstock/streaming/mstock_mapping.py` — ✅
- `broker/mstock/streaming/mstock_adapter.py` — ✅ (equivalent of `smartWebSocketV2`)
- `broker/mstock/mapping/order_data.py` — ✅
- `broker/mstock/mapping/transform_data.py` — ✅
- `broker/mstock/mapping/margin_data.py` — ✅
- `broker/mstock/database/master_contract_db.py` — ✅

## Functions

### `api/data.py`
- `get_quotes` — ✅
- `get_multiquotes` — ✅
- `get_history` — ✅
- `get_depth` — ✅

### `api/funds.py`
- `get_margin_data` — ✅

### `api/order_api.py`
- `get_order_book`, `get_trade_book`, `get_positions`, `get_holdings` — ✅
- `get_open_position` — ✅
- `place_order_api`, `place_smartorder_api` — ✅
- `modify_order`, `cancel_order`, `cancel_all_orders_api` — ✅
- `close_all_positions` — ✅

### `mapping/order_data.py`
- `map_order_data`, `calculate_order_statistics`, `map_trade_data`,
  `map_position_data`, `map_portfolio_data`, `calculate_portfolio_statistics` — ✅

### `mapping/transform_data.py`
- `map_product_type`, `reverse_map_product_type`, `map_variety` — ✅

## Implementation notes

### Quotes & open interest (important)

mstock's REST quote endpoint (`/instruments/quote`) only supports `OHLC` and
`LTP` modes — `FULL` is **rejected with HTTP 400**
(`Invalid mode 'FULL'. Valid modes allowed are OHLC and LTP`). Neither mode
returns open interest, traded volume, or market depth.

Open interest therefore comes from the **binary snap-quote WebSocket feed
(mode 3)** — the only mstock source for OI/depth:

- `get_quotes()` (single symbol) uses REST OHLC. It primarily serves index LTP,
  which carries no OI, so the OHLC snapshot is sufficient.
- `get_multiquotes()` builds an OHLC base via REST, then overlays OI / bid / ask
  from the snap-quote feed via `MstockWebSocket.fetch_quotes_bulk()`, which
  subscribes to every token over a single short-lived connection (skipping the
  blocking login `recv()` that otherwise stalls the socket ~10–15s). This is
  what makes the option chain (`/api/v1/optionchain`) return non-zero OI;
  without it every leg reports `oi: 0` and downstream consumers that skip
  `oi <= 0` rows see an empty chain.
- `get_depth()` uses the same snap-quote feed (`fetch_quote()`, mode 3).

**Caveat:** the snap-quote binary `volume` field is unreliable (returns absurd
values) and is intentionally not surfaced — quote `volume` stays `0`. Live
`bid`/`ask` depth is only populated during market hours.

### Funds & M2M (realised / unrealised)

mstock's Type B `fundsummary` endpoint (`/user/fundsummary`) returns
`REALISED_PROFITS` and `MTM_COMBINED` as `null` **unconditionally** —
account-level M2M is never available there. Mapping those fields straight
through made `/api/v1/funds` always report `m2mrealized: 0.00` and
`m2munrealized: 0.00`.

`get_margin_data()` therefore derives M2M from the **positions feed**
(`/portfolio/positions`), split the same way the mstock web UI does it:

- `netqty == 0` (position fully closed) → `netvalue` counts as **realised**.
- `netqty != 0` (position still open) → `netvalue` counts as **unrealised**.

Balance fields still come straight from `fundsummary`
(`availablecash` ← `AVAILABLE_BALANCE`, `collateral` ← `COLLATERALS`,
`utiliseddebits` ← `AMOUNT_UTILIZED`).

The Type A endpoints that *do* expose realised/unrealised directly (Kite-style)
require a **separate Type A access token** — the Type B session token returns
`TokenException` against them — so they are not usable from this integration.

**Caveat:** for *partially* open positions, `netvalue` (executed sell − buy) is
only the booked component and omits LTP-based MTM on the remaining open qty.
True per-position MTM would need an LTP lookup per leg, too costly for a field
the engine polls every 500 ms. The account total
(`collateral + realised + unrealised`) stays correct, and the fully-closed case
is exact.

### Streaming (real-time WebSocket)

mstock **does not send a login-acknowledgement frame** after `LOGIN:<token>`.
The streaming client (`MstockWebSocket`) therefore confirms login *implicitly*
~0.5s after the socket opens (`_post_login_settle` → `_confirm_login`) rather
than waiting for a string ack that never arrives. Waiting for it would leave
`is_connected()` permanently `False`, so no subscription is ever sent and no
market data flows.

Subscriptions requested before login completes are stored in the adapter
(`MstockWebSocketAdapter.subscriptions`) and flushed to the broker once login
is confirmed, via the `on_login` callback (`_flush_subscriptions`). The same
callback re-subscribes after a reconnect. Each token is subscribed once at its
highest requested mode (1=LTP, 2=Quote, 3=Depth).
