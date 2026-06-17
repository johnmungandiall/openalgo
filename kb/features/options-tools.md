# Feature: Options Trading Suite (`/tools`)

> 12 options analytics tools sharing one data flow: underlying LTP via `get_quotes`, each CE/PE leg via `get_multiquotes`, greeks via `opengreeks`.

## Surfaces (React pages under [frontend/src/pages/](../../frontend/src/pages/))
OptionChain, IVChart, IVSmile, OITracker, OIProfile, MaxPain, StraddleChart, CustomStraddle, VolSurface, GEXDashboard, StrategyBuilder, StrategyPortfolio. Routes in [App.tsx:193-205](../../frontend/src/App.tsx#L193).

## Backend services ([services/](../../services/))
- `option_chain_service.py` — core. Builds strikes around ATM with CE/PE legs + labels (ATM/ITM/OTM). `find_atm_strike_from_actual`, `construct_option_symbol` (via `option_symbol_service`). Header doc shows output shape ([option_chain_service.py:1-46](../../services/option_chain_service.py#L1)).
- `option_greeks_service.py` / `multi_strike_oi_service.py`, `iv_smile_service.py`, `iv_chart_service.py`, `vol_surface_service.py`, `gex_service.py`, `oi_tracker_service.py`, `oi_profile_service.py`, `straddle_chart_service.py`, `custom_straddle_service.py`, `synthetic_future_service.py`, `expiry_service.py`.
- Greeks computed with the `opengreeks` dependency.

## API namespaces ([restx_api/](../../restx_api/))
`/optionchain`, `/optiongreeks`, `/multioptiongreeks`, `/optionsymbol`, `/optionsorder`, `/optionsmultiorder`, `/syntheticfuture`, `/expiry`. See [[api-layer]].

## CRITICAL data-flow gotcha
Consumers (`restx_api` + external apps) **skip any option leg with `oi <= 0`**. So `get_multiquotes` MUST return real `oi` for F&O symbols. Brokers whose REST quote API lacks OI must overlay OI from the snap-quote WebSocket feed, or the **option chain comes back empty**. See [[broker-integration]] and root CLAUDE.md "Quotes/Multiquotes/OI".

## Live updates
Frontend hooks `useOptionChainLive` / `useOptionChainPolling` ([frontend/src/hooks/](../../frontend/src/hooks/)); API client `frontend/src/api/option-chain.ts`.
