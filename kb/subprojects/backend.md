# Subproject: Backend (Flask, repo root)

> Python 3.12 Flask app at repo root. `pyproject.toml` = `openalgoUI`. Run with `uv`. Serves API, UI, webhooks, WS proxy.

- **Entry**: [app.py](../../app.py) `create_app()` ([app.py:131](../../app.py#L131)). Platform version in [utils/version.py](../../utils/version.py) (also `pyproject.toml:4`).
- **Layers** (request → response):
  - Routes: [blueprints/](../../blueprints/) (UI/webhooks) + [restx_api/](../../restx_api/) (`/api/v1`)
  - Logic: [services/](../../services/) — `<name>_service.py`, called by both API and blueprints
  - Broker calls: [broker/](../../broker/) plugins, imported dynamically by name
  - Persistence: [database/](../../database/) SQLAlchemy ORM (no raw SQL)
- **Config**: env via [.sample.env](../../.sample.env) → `.env`; loaded/validated by [utils/env_check.py](../../utils/env_check.py) at top of app.py.
- **Auth model**: web UI = Flask session + CSRF; `/api/v1` = API key (body `apikey` or `X-API-KEY` header), hashed w/ `API_KEY_PEPPER`. Broker login via [blueprints/brlogin.py](../../blueprints/brlogin.py) + per-broker `auth_api.py`.
- **Schedulers**: single APScheduler instance shared by Flow + Historify + Python strategy services (started in app.py background thread).
- **Pkg mgmt**: `uv run app.py`, `uv add <pkg>`, `uv sync`. Lint/format: `uv run ruff check . --fix` / `ruff format .` (line 100, py312).
- **Tests**: `uv run pytest test/ -v` (config in `pyproject.toml [tool.pytest]`).
- **Wires to frontend**: serves `frontend/dist/` via [blueprints/react_app.py](../../blueprints/react_app.py); React calls `/api/v1` + connects SocketIO + WS proxy (8765). See [[frontend]].
