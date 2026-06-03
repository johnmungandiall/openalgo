# OpenAlgo API Contract — what this app expects from the broker server

This document lists **every OpenAlgo endpoint the Qwantonomous Strategy Server calls**, with the
exact request and response shapes. Use it to build a **drop-in replacement server** (your own
data/order backend) that the app can talk to instead of OpenAlgo — if your server answers these
calls in these shapes, the app will not know the difference.

> Scope: **OpenAlgo only.** The app's own loopback relays (ports 1010 / 1011 / 1012 / 1100 / 1200 /
> 1300) are *not* covered here — they are outputs the app hosts, not a backend it consumes.

---

## 1. Connection settings

The app reads two base addresses (defaults shown; both configurable in `settings.json`, and in
Pro/Trato mode they are pushed from the subscription row):

| Setting | Default | Used for |
|---|---|---|
| `BROKER_API_BASE_URL` | `http://127.0.0.1:5001` | All REST calls below |
| `WS_URL` | `ws://127.0.0.1:8765` | The live market-data WebSocket |
| `API_KEY` | *(local secret, DPAPI-stored)* | Auth on every REST + WS call |

Your server must therefore:
- Serve **HTTP REST** at `BROKER_API_BASE_URL` (path prefix `/api/v1/`).
- Serve a **WebSocket** at `WS_URL`.
- Accept the app's `API_KEY` as the auth token (you decide how to validate it — the app just sends
  whatever string it has).

### Exchange codes the app sends

The app derives the exchange from the symbol/index — your server must accept these strings:

| Index | Option leg exchange | Underlying/index exchange |
|---|---|---|
| NIFTY | `NFO` | `NSE_INDEX` |
| BANKNIFTY | `NFO` | `NSE_INDEX` |
| SENSEX | `BFO` | `BSE_INDEX` |

---

## 2. REST API

All REST calls are **`POST`** with header `Content-Type: application/json` and a JSON body, **except
`/ticker` which is `GET`** (params in the query string). Every body carries the key `apikey`.

Response convention: most endpoints return `{ "status": "...", "data": { ... } }` (or `data` as an
array). The app reads the documented fields below and ignores everything else, so extra fields are
harmless.

### 2.1 `POST /api/v1/funds` — account balance & PnL

Request:
```json
{ "apikey": "<API_KEY>" }
```
Response (the app reads `data`):
```json
{
  "data": {
    "collateral": 100000.0,
    "m2mrealized": 0.0,
    "m2munrealized": 0.0,
    "availablecash": 100000.0,
    "utiliseddebits": 0.0
  }
}
```
- `collateral`, `m2mrealized`, `m2munrealized` are **required** — if any is missing/non-numeric the
  app skips the poll (no phantom zero on the chart).
- `availablecash`, `utiliseddebits` are **optional** (older builds may omit them; they feed the
  BAL / USED readouts).
- The app's total PnL = `collateral + m2mrealized + m2munrealized`.
- Polled every **500 ms** while the engine runs.

### 2.2 `POST /api/v1/positionbook` — open positions

Request:
```json
{ "apikey": "<API_KEY>" }
```
Response — `data` is an array (the app also accepts a bare top-level array):
```json
{
  "data": [
    {
      "symbol": "NIFTY12MAY2624750CE",
      "quantity": 75,
      "average_price": 120.5,
      "ltp": 138.0
    }
  ]
}
```
Field aliases the app accepts (either spelling works):
- symbol: `symbol` **or** `tradingsymbol`
- quantity: `quantity` **or** `netqty`
- avg price: `average_price` **or** `averageprice`
- last price: `ltp` **or** `last_price`

Closed rows (`quantity == 0`) are ignored. Used for the open-positions table and PAPER-mode PnL.

### 2.3 `POST /api/v1/expiry` — available expiries

Request:
```json
{ "apikey": "<API_KEY>", "symbol": "NIFTY", "exchange": "NSE_INDEX", "instrumenttype": "options" }
```
Response — `data` is an array of expiry strings in `DDMMMYY` (or `DD-MMM-YYYY`) format:
```json
{ "data": ["12MAY26", "19MAY26", "29MAY26"] }
```
The app parses, drops past-dated entries, and sorts ascending.

### 2.4 `POST /api/v1/optionchain` — full option chain (LTP-mode fetch)

Request:
```json
{ "apikey": "<API_KEY>", "underlying": "NIFTY", "exchange": "NSE_INDEX", "expiry_date": "12MAY26" }
```
Response — note the array is under **`chain`**, not `data`:
```json
{
  "chain": [
    {
      "ce": { "symbol": "NIFTY12MAY2624750CE", "ltp": 120.5, "oi": 12345 },
      "pe": { "symbol": "NIFTY12MAY2624750PE", "ltp": 98.0,  "oi": 9876 }
    }
  ]
}
```
Each chain row has a `ce` and a `pe` object; the app reads `symbol`, `ltp`, `oi` from each. Rows
with `oi <= 0` or `ltp <= 0` are skipped. (Only used in **LTP selection mode**; ATM mode builds
symbols locally from the index spot and never calls this.)

### 2.5 `POST /api/v1/quotes` — single-symbol snapshot LTP

Request:
```json
{ "apikey": "<API_KEY>", "symbol": "NIFTY12MAY2624750CE", "exchange": "NFO" }
```
Response (the app reads `data.ltp`, accepts `last_price` alias):
```json
{ "data": { "ltp": 138.0 } }
```

### 2.6 `POST /api/v1/placeorder` — place an order

Request (note **`apikey`** spelling, all values are strings):
```json
{
  "apikey": "<API_KEY>",
  "strategy": "QwantStrategy",
  "symbol": "NIFTY12MAY2624750CE",
  "exchange": "NFO",
  "action": "BUY",
  "pricetype": "MARKET",
  "product": "MIS",
  "quantity": "75"
}
```
Response (any/all fields optional; the app reads them for logging):
```json
{ "orderid": "250512000123", "status": "success", "message": "..." }
```
- order id: `orderid` **or** `order_id`
- error text: `message` **or** `error`

### 2.7 `POST /api/v1/closeposition` — square off all positions

Request:
```json
{ "apikey": "<API_KEY>", "strategy": "QwantStrategy" }
```
Response: `{ "status": "...", "message": "..." }`.
- **HTTP 500 is treated as "no open positions" (soft no-op), not an error.** Return 500 when there
  is nothing to close, matching OpenAlgo.

### 2.8 `POST /api/v1/analyzer` + `POST /api/v1/analyzer/toggle` — paper/live mode

`/analyzer` (read): request `{ "apikey": "<API_KEY>" }` → `{ "data": { "analyze_mode": true } }`
`/analyzer/toggle` (set): request `{ "apikey": "<API_KEY>", "mode": false }` → `{ "data": { "analyze_mode": false } }`

`analyze_mode: true` = PAPER (simulated orders), `false` = LIVE. Must be a real JSON boolean.

### 2.9 `GET /api/v1/ticker/{symbol}` — historical candles (startup seed)

The **only GET** endpoint. `apikey` and params go in the query string:
```
GET /api/v1/ticker/NIFTY?apikey=<API_KEY>&interval=5m&from=2026-05-30&to=2026-05-31&format=json
```
Response:
```json
{
  "status": "success",
  "data": [
    { "timestamp": 1716960600, "open": 24700, "high": 24750, "low": 24690, "close": 24720 }
  ]
}
```
Only `5m` interval is wired up today. Optional — if you don't serve it, the chart just starts with
no previous-day history (the app degrades gracefully).

### 2.10 `POST /api/v1/syntheticfuture` — optional

Only called when `SyntheticFutureService` is active (a composite CE+PE+underlying synthetic-future
feed). Optional; safe to leave unimplemented unless you enable that feature.

---

## 3. WebSocket API (`WS_URL`)

A single text-frame JSON protocol. Sequence: **authenticate → (500 ms) → subscribe → receive
`market_data` frames**. The app opens several independent sockets (strategy leg, each index, broker
info, etc.) — your server must allow the **app process** to hold multiple concurrent connections.

### 3.1 Authenticate

Client → server (first frame on every socket):
```json
{ "action": "authenticate", "api_key": "<API_KEY>" }
```
Server → client (optional but recommended — some app sockets subscribe on this ack, others rely on
a fixed 500 ms delay, so either behaviour works):
```json
{ "type": "auth", "status": "success", "broker": "yourbroker" }
```

### 3.2 Subscribe — **two shapes, support both**

**Shape A — multi-symbol array (used by the strategy engine's option leg, `mode: 1`):**
```json
{ "action": "subscribe", "symbols": [ { "exchange": "NFO", "symbol": "NIFTY12MAY2624750CE" } ], "mode": 1 }
```

**Shape B — single symbol (used by index / quote sockets, `mode: 2`):**
```json
{ "action": "subscribe", "symbol": "NIFTY", "exchange": "NSE_INDEX", "mode": 2 }
```

Modes: `1` = LTP only, `2` = quote (LTP **+** previous `close`). Treat each single-symbol subscribe
as a **replace** is fine — the app deliberately opens one socket per symbol for mode-2 to avoid
cross-talk.

Subscribe ack (optional):
```json
{ "type": "subscribe", "subscriptions": [ { "symbol": "...", "exchange": "...", "status": "success" } ] }
```
On failure set `"status": "error"` and include a `"message"`.

### 3.3 Market data — the tick frame

Server → client, pushed on every price update:
```json
{ "type": "market_data", "symbol": "NIFTY12MAY2624750CE", "data": { "ltp": 138.0, "close": 132.0 } }
```
- `data.ltp` — **required**, the live price. Without it the tick is dropped.
- `data.close` — yesterday's close; only needed for `mode: 2` (drives the index %-change badge).
- `open` / `high` / `low` / `volume` may be present but the app ignores them for indices (broker
  sentinel values like `2147483648` are common there).

### 3.4 Unsubscribe

```json
{ "action": "unsubscribe", "symbols": [ { "exchange": "NFO", "symbol": "NIFTY12MAY2624750CE" } ] }
```

### 3.5 Broker info (optional)

Client → `{ "action": "get_broker_info" }`. Server → 
```json
{ "type": "broker_info", "status": "success", "broker": "flattrade", "adapter_status": "connected", "user_id": "..." }
```
Drives the bottom-bar broker-name readout. Optional — if omitted, the readout just shows `--`.

---

## 4. Minimum viable server (checklist)

To make the app fully functional against your own backend, implement:

**Required for live trading:**
- WS: `authenticate`, `subscribe` (both shapes), `market_data` push, `unsubscribe`
- REST: `/funds`, `/positionbook`, `/expiry`, `/optionchain` (or use ATM mode), `/quotes`,
  `/placeorder`, `/closeposition`, `/analyzer`, `/analyzer/toggle`

**Optional (graceful degradation if missing):**
- REST: `/ticker/{symbol}` (no startup history), `/syntheticfuture` (feature off)
- WS: `get_broker_info` (broker name shows `--`)

**Behavioural contracts that matter:**
- `/closeposition` returns **HTTP 500** when there are no positions (soft no-op).
- `/funds` must always include `collateral`, `m2mrealized`, `m2munrealized`.
- `market_data.data.ltp` must be present on every tick.
- Accept all the field-name aliases listed above (the app reads either spelling).
- Allow the app process to open **multiple concurrent WebSocket connections**.

---

*Generated from the service code in `lib/services/` — keep in sync with:
`market_data_ws_service.dart`, `index_price_service.dart`, `pnl_service.dart`,
`paper_pnl_service.dart`, `option_symbols_fetch_service.dart`, `expiry_service.dart`,
`order_placement_service.dart`, `analyzer_mode_service.dart`, `historical_data_service.dart`,
`broker_info_service.dart`.*
