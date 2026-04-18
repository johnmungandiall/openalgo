# Pi42 Integration - Phase 3 Complete

## Summary

Successfully completed Phase 3 (Week 5-6) of Pi42 cryptocurrency futures exchange integration into OpenAlgo - WebSocket streaming implementation.

## Completed Tasks

### Week 5: WebSocket Foundation ✅

1. **WebSocket Connection Manager**
   - Created [websocket_client.py](broker/pi42/streaming/websocket_client.py)
   - `Pi42WebSocketClient` class with full connection lifecycle
   - Thread-based connection management
   - WebSocket URL: `wss://stream.pi42.com/ws`

2. **Authentication**
   - HMAC-SHA256 signature for WebSocket auth
   - Auth message format: `{'method': 'auth', 'params': {...}}`
   - Automatic authentication on connection
   - Auth status tracking

3. **Heartbeat Mechanism**
   - Automatic ping/pong every 30 seconds
   - Heartbeat monitoring thread
   - Connection health tracking
   - Timeout detection

4. **Reconnection Logic**
   - Automatic reconnection on disconnect
   - Exponential backoff (5s × attempt number)
   - Max 10 reconnection attempts
   - Automatic resubscription after reconnect

5. **Message Routing**
   - Event-based message routing
   - Channel-based subscription system
   - Multiple callbacks per channel
   - Error handling for callbacks

### Week 6: Real-Time Data Streams ✅

1. **Market Data Streams**
   - Created [market_data_stream.py](broker/pi42/streaming/market_data_stream.py)
   - `Pi42MarketDataStream` class

   **Supported Streams:**
   - **Ticker** (`ticker@SYMBOL`): 24hr ticker with price, volume, OI, funding rate
   - **Depth** (`depth5@SYMBOL`, `depth10@SYMBOL`, `depth20@SYMBOL`): Order book depth
   - **Trades** (`trade@SYMBOL`): Recent trades with buyer/seller info
   - **Kline** (`kline_1m@SYMBOL`, etc.): Candlestick data (1m, 5m, 15m, 1h, 4h, 1d)
   - **Mark Price** (`markPrice@SYMBOL`): Mark price, index price, funding rate
   - **Liquidation** (`forceOrder@SYMBOL`): Liquidation orders

2. **User Data Streams**
   - Created [user_data_stream.py](broker/pi42/streaming/user_data_stream.py)
   - `Pi42UserDataStream` class

   **Supported Events:**
   - **Order Updates** (`ORDER_TRADE_UPDATE`): Order status, fills, trades
   - **Account Updates** (`ACCOUNT_UPDATE`): Balance and position changes
   - **Margin Call** (`MARGIN_CALL`): Margin call warnings
   - **Config Updates** (`ACCOUNT_CONFIG_UPDATE`): Leverage and settings changes

3. **Position & Balance Streams**
   - `Pi42PositionStream` - Real-time position updates
   - `Pi42BalanceStream` - Real-time balance updates
   - Dedicated streams for focused monitoring

4. **OpenAlgo Integration**
   - Created [broker_adapter.py](broker/pi42/streaming/broker_adapter.py)
   - `Pi42BrokerAdapter` class for WebSocket proxy integration
   - ZeroMQ message publishing
   - Unified subscription management
   - Active subscription tracking

## Architecture

### WebSocket Client Flow

```
User → Pi42BrokerAdapter → Pi42WebSocketClient → Pi42 WebSocket Server
                ↓
         ZeroMQ Publisher → OpenAlgo WebSocket Proxy → Frontend
```

### Connection Lifecycle

1. **Connect**: Establish WebSocket connection
2. **Authenticate**: Send auth message with HMAC signature
3. **Subscribe**: Subscribe to channels
4. **Receive**: Process incoming messages
5. **Heartbeat**: Send ping every 30s
6. **Reconnect**: Auto-reconnect on disconnect
7. **Resubscribe**: Restore subscriptions after reconnect

### Message Flow

```
Pi42 WebSocket → WebSocketClient._on_message()
                      ↓
                 _route_message()
                      ↓
                 Channel callbacks
                      ↓
                 Stream processors (market/user)
                      ↓
                 BrokerAdapter._publish_message()
                      ↓
                 ZeroMQ Publisher
```

## Usage Examples

### Basic WebSocket Connection

```python
from broker.pi42.streaming.websocket_client import create_websocket_client

# Create and connect
ws_client = create_websocket_client(auth_token)
ws_client.connect()

# Subscribe to channel
def on_ticker(data):
    print(f"Ticker: {data}")

ws_client.subscribe('ticker@BTCUSDT', on_ticker)

# Disconnect
ws_client.disconnect()
```

### Market Data Streaming

```python
from broker.pi42.streaming.market_data_stream import Pi42MarketDataStream

market_stream = Pi42MarketDataStream(ws_client)

# Subscribe to ticker
def on_ticker(data):
    print(f"Price: {data['last_price']}, Volume: {data['volume']}")

market_stream.subscribe_ticker('BTCUSDT', on_ticker)

# Subscribe to depth
def on_depth(data):
    print(f"Best bid: {data['bids'][0]}, Best ask: {data['asks'][0]}")

market_stream.subscribe_depth('BTCUSDT', on_depth, levels=5)

# Subscribe to trades
def on_trade(data):
    print(f"Trade: {data['price']} x {data['quantity']}")

market_stream.subscribe_trades('BTCUSDT', on_trade)
```

### User Data Streaming

```python
from broker.pi42.streaming.user_data_stream import Pi42UserDataStream

user_stream = Pi42UserDataStream(ws_client)

# Subscribe to all user events
def on_user_data(data):
    event_type = data['event_type']
    
    if event_type == 'order':
        print(f"Order {data['order_id']}: {data['order_status']}")
    elif event_type == 'account':
        print(f"Positions: {len(data['positions'])}")
        print(f"Balances: {len(data['balances'])}")
    elif event_type == 'margin_call':
        print(f"MARGIN CALL! Positions at risk: {len(data['positions'])}")

user_stream.start_user_stream(on_user_data)
```

### OpenAlgo Integration

```python
from broker.pi42.streaming.broker_adapter import create_broker_adapter

# Create adapter with ZeroMQ publisher
adapter = create_broker_adapter(auth_token, zmq_publisher)

# Subscribe to market data
adapter.subscribe_ticker('BTCUSDT')
adapter.subscribe_depth('BTCUSDT', levels=5)
adapter.subscribe_trades('BTCUSDT')

# Subscribe to user data
adapter.subscribe_orders()
adapter.subscribe_positions()
adapter.subscribe_balance()

# Check status
print(f"Connected: {adapter.is_connected()}")
print(f"Authenticated: {adapter.is_authenticated()}")
print(f"Subscriptions: {adapter.get_active_subscriptions()}")

# Unsubscribe
adapter.unsubscribe_ticker('BTCUSDT')
adapter.disconnect()
```

## File Structure

```
broker/pi42/streaming/
├── websocket_client.py       # WebSocket connection manager (NEW)
├── market_data_stream.py     # Market data streams (NEW)
├── user_data_stream.py       # User data streams (NEW)
└── broker_adapter.py         # OpenAlgo integration (NEW)
```

## WebSocket Channels

### Market Data Channels

| Channel | Format | Description |
|---------|--------|-------------|
| Ticker | `ticker@SYMBOL` | 24hr ticker statistics |
| Depth | `depth5@SYMBOL` | Order book depth (5/10/20 levels) |
| Trades | `trade@SYMBOL` | Recent trades |
| Kline | `kline_1m@SYMBOL` | Candlestick data |
| Mark Price | `markPrice@SYMBOL` | Mark price and funding rate |
| Liquidation | `forceOrder@SYMBOL` | Liquidation orders |

### User Data Channels

| Channel | Event Type | Description |
|---------|------------|-------------|
| userData | ORDER_TRADE_UPDATE | Order status changes |
| userData | ACCOUNT_UPDATE | Balance/position updates |
| userData | MARGIN_CALL | Margin call warnings |
| userData | ACCOUNT_CONFIG_UPDATE | Leverage/config changes |

## Message Formats

### Ticker Message

```json
{
  "event_type": "ticker",
  "symbol": "BTCUSDT",
  "last_price": 50000.0,
  "open_price": 49000.0,
  "high_price": 51000.0,
  "low_price": 48500.0,
  "volume": 1234.56,
  "open_interest": 5000.0,
  "mark_price": 50010.0,
  "funding_rate": 0.0001
}
```

### Order Update Message

```json
{
  "event_type": "order",
  "symbol": "BTCUSDT",
  "order_id": "12345",
  "order_status": "FILLED",
  "side": "BUY",
  "order_type": "LIMIT",
  "quantity": 0.1,
  "price": 50000.0,
  "cumulative_filled_quantity": 0.1,
  "realized_profit": 10.5
}
```

### Position Update Message

```json
{
  "symbol": "BTCUSDT",
  "position_amount": 0.5,
  "entry_price": 50000.0,
  "mark_price": 51000.0,
  "unrealized_pnl": 500.0,
  "leverage": 10,
  "liquidation_price": 45250.0
}
```

## Features

### Connection Management
- Automatic connection establishment
- Thread-based async operation
- Clean disconnect handling
- Connection status tracking

### Authentication
- HMAC-SHA256 signature
- Automatic auth on connect
- Auth status verification
- Secure credential handling

### Heartbeat & Health
- 30-second ping interval
- Pong response monitoring
- Connection health tracking
- Timeout detection

### Reconnection
- Automatic reconnect on disconnect
- Exponential backoff strategy
- Max 10 attempts
- Subscription restoration

### Subscription Management
- Channel-based subscriptions
- Multiple callbacks per channel
- Subscribe/unsubscribe support
- Active subscription tracking

### Message Processing
- Event-based routing
- Type-specific handlers
- Data transformation
- Error handling

### OpenAlgo Integration
- ZeroMQ message publishing
- Unified subscription API
- Status monitoring
- Multi-broker support

## Dependencies

```python
# Required packages
websocket-client  # WebSocket client library
```

Add to requirements:
```bash
websocket-client>=1.6.0
```

## Next Steps - Phase 4

Phase 4 will implement funds and account management:

1. **Week 7: Funds API**
   - Get account balance
   - Get margin info
   - Transfer between wallets
   - Transaction history

2. **Week 8: Account Management**
   - Account info API
   - Trading fee rates
   - API key permissions
   - Account activity logs

---

**Status**: Phase 3 Complete ✅  
**Date**: 2026-04-18  
**Next**: Begin Phase 4 - Funds & Account Management
