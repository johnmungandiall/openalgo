# Feature: WebSocket Market-Data Streaming

> Three-layer pipeline: broker adapter → ZeroMQ bus → unified WS proxy → browser. Decouples broker feed from slow clients.

## Layers
1. **Broker adapter** [broker/<name>/streaming/<name>_adapter.py] (subclass of [websocket_proxy/base_adapter.py](../../websocket_proxy/base_adapter.py)): connects to broker's proprietary feed, normalizes ticks, **publishes to ZeroMQ PUB**. Pool: `MAX_SYMBOLS_PER_WEBSOCKET`(1000) × `MAX_WEBSOCKET_CONNECTIONS`(3) = 3000 symbols.
2. **ZeroMQ bus** (port 5555, loopback): `zmq.PUB` bound in `_bind_to_available_port` ([base_adapter.py:206](../../websocket_proxy/base_adapter.py#L206)); host/port via `ZMQ_HOST`/`ZMQ_PORT`. Also used for cache-invalidation events.
3. **Unified WS proxy** (port 8765) [websocket_proxy/server.py](../../websocket_proxy/server.py) `WebSocketProxy` ([:34](../../websocket_proxy/server.py#L34)): authenticates clients (API key), manages subscriptions, subscribes to ZMQ, delivers filtered/throttled ticks. Refuses to start if 8765 busy ([:53](../../websocket_proxy/server.py#L53)) — port is fixed for SDK clients.

## Wiring
- Adapter chosen by [websocket_proxy/broker_factory.py](../../websocket_proxy/broker_factory.py) `create_broker_adapter()`.
- Proxy launched from [app.py:889](../../app.py#L889) `start_websocket_proxy(app)` ([websocket_proxy/app_integration.py](../../websocket_proxy/app_integration.py)) — child **process** under eventlet, OS **thread** on dev server. Docker runs it separately (`start.sh`); detected via `/.dockerenv` ([app.py:873](../../app.py#L873)).
- Modes/labels normalized in [websocket_proxy/mode_utils.py](../../websocket_proxy/mode_utils.py); client subscription mgmt in [connection_manager.py](../../websocket_proxy/connection_manager.py).
- Frontend consumes via `useSocket`/`useLivePrice`/`useMarketData` hooks → [services/websocket_service.py](../../services/websocket_service.py) / `websocket_client.py`.

## Gotcha: connect → login → subscribe race
`adapter.connect()` returns immediately (background thread). Subscriptions can arrive before auth. Must (1) confirm login (some brokers send NO ack — confirm implicitly, don't block on `recv()`), (2) flush early subscriptions on login + after reconnect, or symbols tick in OpenAlgo's view but never on the broker. Verify with a **fresh** symbol → expect a `market_data` frame even when market closed. See [[broker-integration]].
