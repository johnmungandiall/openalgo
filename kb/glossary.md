# Glossary

> Domain & project terms. Trading/Indian-market terms a non-trader won't know, plus OpenAlgo-specific names.

## OpenAlgo-specific
- **Surface** — one of the 4 products in a deployment: Broker API, Python host, Flow, Options Suite. See [[overview]].
- **Analyzer / Sandbox mode** — paper-trading mode; orders go to the sandbox engine, not the broker. Toggled by `get_analyze_mode()`. See [[sandbox-analyzer]].
- **Smart order** — order with `position_size` target; engine computes delta vs current position (may result in `order.no_action`).
- **Master contract** — the broker's full instrument list, downloaded into the `SymToken` table (`broker/*/database/master_contract_db.py`).
- **SymToken** — symbol-mapping table: OpenAlgo symbol ↔ broker symbol/token. See [[conventions]].
- **Plugin / capabilities** — each broker's `plugin.json` (`supported_exchanges`, `broker_type`, `leverage_config`). See [[broker-integration]].
- **Action Center** — order-approval workflow: Auto (direct) vs Semi-Auto (manual approve).
- **Flow** — no-code node-graph strategy builder. **Historify** — historical data downloader/charts (DuckDB).
- **EventBus** — in-process pub/sub for order side-effects (`utils/event_bus.py`).

## Trading / Indian market
- **F&O / FNO** — Futures & Options. **NFO/BFO** — NSE/BSE F&O exchanges; **MCX** — commodities; **CDS/BCD** — currency derivatives.
- **OI (Open Interest)** — outstanding contracts; key options metric. Legs with `oi<=0` are dropped (see [[options-tools]]).
- **LTP** — Last Traded Price. **Depth** — order-book bid/ask levels (5/20/30/50).
- **M2M** — Mark-to-Market P&L; **realized** (closed positions) vs **unrealized** (open).
- **ATM/ITM/OTM** — At/In/Out-of-the-Money option strikes relative to spot.
- **Greeks** — option risk sensitivities (delta/gamma/theta/vega); computed via `opengreeks`.
- **GEX** — Gamma Exposure. **Max Pain** — strike minimizing total option payout. **Vol Surface / IV Smile** — implied-vol across strikes/expiries.
- **Straddle** — same-strike CE+PE position. **Synthetic future** — CE−PE replicating a future.
- **Product types**: **CNC** (delivery), **NRML** (F&O carry), **MIS** (intraday auto-squareoff).
- **Square-off** — force-close intraday positions at exchange cutoff. **T+1 settlement** — next-day settlement (modeled in sandbox).
- **GTT** — Good-Till-Triggered order. **GIFTNIFTY** — NSE IFSC index (in `GLOBAL_INDEX`).
- **SEBI static IP mandate** (Apr 1 2026) — transactional orders require broker-side IP whitelisting. See root CLAUDE.md.
