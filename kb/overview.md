# Overview

> OpenAlgo: self-hosted algo-trading platform. Flask backend + React 19 SPA, one broker session shared by 4 surfaces. **Single user per deployment.**

- **What it does**: unified trading API across 33 Indian/crypto brokers, plus in-browser strategy hosting, a no-code Flow builder, and an options analytics suite. See [[glossary]] for domain terms.
- **Tech stack**:
  - Backend: Python 3.12, Flask 3.1, Flask-RESTX (`/api/v1`), Flask-SocketIO, SQLAlchemy 2, APScheduler, httpx[http2], pyzmq, websockets. Pkg mgr: **uv** (never global Python).
  - Frontend: React 19, TypeScript, Vite 7, shadcn/ui (Radix), TanStack Query, Zustand, react-router 7, lightweight-charts, plotly, @xyflow/react (Flow). Lint: Biome.
  - Data: 5 SQLite DBs + 1 DuckDB (historical). See [[architecture]].
- **Four surfaces** (all share one broker session + WS feed):
  - Unified Broker API `/api/v1/` — external platforms (TradingView, Amibroker, ChartInk, Excel, Python, MCP)
  - Python Strategy Host `/python` — in-browser editor, scheduled subprocess strategies
  - Flow (no-code) `/flow` — drag-drop node graph → orders
  - Options Suite `/tools` — option chain, IV smile, max pain, vol surface, GEX, OI tracker, straddle, etc.
- **Entry point**: [app.py](../app.py) → `create_app()` ([app.py:131](../app.py#L131)), `setup_environment()` ([app.py:579](../app.py#L579)). Dev server at bottom (`socketio.run`, [app.py:998](../app.py#L998)).
- **How to run**:
  - `cp .sample.env .env`; generate `APP_KEY`/`API_KEY_PEPPER` via `uv run python -c "import secrets; print(secrets.token_hex(32))"`
  - Dev: `uv run app.py` → http://127.0.0.1:5000 (React SPA at `/`; in-app API explorer at `/playground` — Flask-RESTX Swagger UI is disabled, `Api(doc=False)`)
  - Prod (Linux): `uv run gunicorn --worker-class eventlet -w 1 app:app` (**must be `-w 1`**)
  - Frontend dev: `cd frontend && npm install && npm run build` (only when editing React; CI commits `dist/` to `main`)
- **Tests**: `uv run pytest test/ -v`; frontend `npm test` / `npm run e2e`. Most testing is manual via UI / `/api/docs` / `/analyzer`.
- **Repo**: https://github.com/marketcalls/openalgo · **Docs**: https://docs.openalgo.in

last indexed: 2026-06-17 (branch kotak-update, base commit dcb674e2)
