# Feature: REST API Layer (`/api/v1/`)

> Flask-RESTX API for external platforms (TradingView, Amibroker, ChartInk, Excel, Python SDK, MCP). API-key auth, ~50 namespaces.

## Wiring
- [restx_api/__init__.py](../../restx_api/__init__.py): `api_v1_bp` Blueprint `url_prefix="/api/v1"` ([:4](../../restx_api/__init__.py#L4)); `Api(..., doc=False)` ([:5](../../restx_api/__init__.py#L5)) → **built-in Swagger UI disabled** (use React `/playground` instead). Namespaces added [:61-106](../../restx_api/__init__.py#L61).
- Registered + CSRF-exempted in [app.py:242-245](../../app.py#L242).
- Each namespace file is a thin REST wrapper that validates input (schemas in `schemas.py`/`data_schemas.py`/`account_schema.py`) and calls the matching [services/](../../services/) function.

## Namespace → path map (selected)
| Path | File / service |
| --- | --- |
| `/placeorder`,`/placesmartorder`,`/modifyorder`,`/cancelorder`,`/cancelallorder`,`/closeposition` | order services |
| `/basketorder`,`/splitorder`,`/optionsorder`,`/optionsmultiorder` | batch order services |
| `/quotes`,`/multiquotes`,`/depth`,`/history`,`/intervals`,`/ticker`,`/search`,`/symbol` | data services |
| `/optionchain`,`/optiongreeks`,`/multioptiongreeks`,`/optionsymbol`,`/syntheticfuture`,`/expiry` | options ([[options-tools]]) |
| `/funds`,`/margin`,`/orderbook`,`/tradebook`,`/positionbook`,`/holdings`,`/openposition`,`/orderstatus` | account services |
| `/placegttorder`,`/modifygttorder`,`/cancelgttorder`,`/gttorderbook` | GTT services |
| `/analyzer`,`/ping`,`/telegram`,`/whatsapp`,`/instruments`,`/chart`,`/market/holidays`,`/market/timings`,`/pnl` | misc |

## Auth
API key in body `{"apikey": ...}` (recommended for external platforms that can't set headers) or `X-API-KEY` header. Verified via [database/auth_db.py](../../database/auth_db.py) `verify_api_key`; keys hashed with `API_KEY_PEPPER`, generated at `/apikey`.

## Rate limiting
Flask-Limiter ([limiter.py](../../limiter.py)); 429 → JSON for `/api/`, redirect to `/rate-limited` for web ([app.py:539](../../app.py#L539)).

External SDK: PyPI `openalgo` pkg (pinned in `pyproject.toml`/`requirements*.txt`) — separate from platform version. See root CLAUDE.md "Version Bumping".
