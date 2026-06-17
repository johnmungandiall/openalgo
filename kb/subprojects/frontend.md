# Subproject: Frontend (React 19 SPA)

> [frontend/](../../frontend/) — Vite + TS SPA, built to `frontend/dist/`, served by Flask. Own `package.json` (`name: frontend`).

- **Entry**: [frontend/src/main.tsx](../../frontend/src/main.tsx) → [App.tsx](../../frontend/src/App.tsx) (all routes, lazy-loaded). Routing = react-router 7 `BrowserRouter`.
- **Layout split** ([App.tsx:173](../../frontend/src/App.tsx#L173), [:272](../../frontend/src/App.tsx#L272)): most pages under `<Layout>`; canvas/full pages (Playground, Historify, Flow editor) under `<FullWidthLayout>`. Auth gate = `<AuthSync>`.
- **Source tree** ([frontend/src/](../../frontend/src/)):
  - `pages/` — one per route (Dashboard, Positions, OptionChain, StrategyBuilder…); subdirs `flow/`, `strategy/`, `python-strategy/`, `chartink/`, `admin/`, `telegram/`, `whatsapp/`, `monitoring/`
  - `api/` — typed clients per domain (`trading.ts`, `option-chain.ts`, `flow.ts`…); shared axios in `api/client.ts`
  - `stores/` — Zustand: `authStore`, `brokerStore`, `sessionStore`, `themeStore`, `alertStore`, `flowWorkflowStore`
  - `hooks/` — `useSocket`, `useLivePrice`, `useMarketData`, `useOptionChainLive`, `useOrderEventRefresh`…
  - `components/` — `ui/` (shadcn), plus `trading/`, `flow/`, `option-chain/`, `strategy-builder/`, `socket/`, `auth/`, `layout/`
- **Server state**: TanStack Query (`useQuery`); **client state**: Zustand. Live updates: SocketIO (`useSocket`) + WS proxy (`useLivePrice`/market-data hooks).
- **Broker-capability route guards** ([App.tsx:99-115](../../frontend/src/App.tsx#L99)): Leverage page only if `capabilities.leverage_config`; Holdings hidden for `broker_type === 'crypto'`. Caps come from backend plugin.json (see [[features/broker-integration]]).
- **Build**: `npm run build` (`tsc -b && vite build`) → `dist/`. CI force-commits `dist/` to `main`; backend-only devs don't build. Lint `npm run lint` (Biome). Tests: vitest + Playwright e2e.
- **Wires to backend**: same-origin `/api/v1`, SocketIO, ws://host:8765. See [[backend]].
