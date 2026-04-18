# Pi42 WebSocket Implementation Plan

## Overview

Pi42 provides real-time WebSocket streams for order updates, position changes, trades, and funding fees. This document details the WebSocket implementation for crypto futures trading.

## WebSocket Architecture

### 1. Pi42 WebSocket Endpoints

| Type | URL | Purpose |
|------|-----|---------|
| **Public** | `wss://fawss.pi42.com/market-stream` | Market data (ticker, depth, trades) |
| **Authenticated** | `wss://fawss-uds.pi42.com/auth-stream` | User data (orders, positions, trades) |

### 2. Authentication Methods

Pi42 supports two WebSocket authentication methods:

#### Method 1: Listen Key (Recommended)
```javascript
// 1. Create listen key via REST API
POST /v1/retail/listen-key

// 2. Connect to WebSocket with listen key
wss://fawss-uds.pi42.com/auth-stream?listenKey=YOUR_LISTEN_KEY

// 3. Keep alive every 30 minutes
PUT /v1/retail/listen-key
```

#### Method 2: Direct Signature
```javascript
// Connect with api-key and signature in URL params
wss://fawss-uds.pi42.com/auth-stream?api-key=KEY&signature=SIG&timestamp=TS
```

### 3. Event Types

**Authenticated Stream Events:**
- `orderUpdate` - Order status changes
- `positionUpdate` - Position changes (PnL, margin, liquidation price)
- `newTrade` - Trade execution
- `fundingFee` - Funding fee deduction
- `marginCallAlert` - Margin call warning
- `liquidationAlert` - Liquidation warning

**Public Stream Events:**
- `ticker` - 24hr ticker updates
- `depth` - Order book updates
- `aggTrade` - Aggregated trades
- `markPrice` - Mark price updates
- `kline` - Candlestick updates

## Implementation: `broker/pi42/streaming/pi42_adapter.py`

```python
"""
Pi42 WebSocket Adapter

Handles real-time WebSocket connections for crypto futures trading.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

from broker.pi42.api.auth_api import (
    create_auth_instance,
    create_listen_key,
    update_listen_key,
    delete_listen_key
)
from utils.logging import get_logger

logger = get_logger(__name__)


class Pi42WebSocketAdapter:
    """WebSocket adapter for Pi42 crypto futures."""
    
    def __init__(self, auth_token: str):
        """
        Initialize Pi42 WebSocket adapter.
        
        Args:
            auth_token: Authentication token
        """
        self.auth_token = auth_token
        self.auth_ws_url = "wss://fawss-uds.pi42.com/auth-stream"
        self.public_ws_url = "wss://fawss.pi42.com/market-stream"
        
        # WebSocket connections
        self.auth_ws = None
        self.public_ws = None
        
        # Listen key management
        self.listen_key = None
        self.listen_key_update_task = None
        
        # Subscriptions
        self.subscribed_symbols: Set[str] = set()
        self.callbacks: Dict[str, List[Callable]] = {}
        
        # Connection state
        self.is_connected = False
        self.is_running = False
        
        logger.info("Pi42 WebSocket adapter initialized")
    
    async def connect(self):
        """Establish WebSocket connections."""
        try:
            logger.info("Connecting to Pi42 WebSocket")
            
            # Create listen key for authenticated stream
            self.listen_key, error = create_listen_key(self.auth_token)
            
            if error:
                logger.error(f"Failed to create listen key: {error}")
                raise Exception(f"Listen key creation failed: {error}")
            
            logger.info("Listen key created successfully")
            
            # Connect to authenticated stream
            auth_url = f"{self.auth_ws_url}?listenKey={self.listen_key}"
            self.auth_ws = await websockets.connect(auth_url)
            
            logger.info("Connected to authenticated stream")
            
            # Connect to public stream
            self.public_ws = await websockets.connect(self.public_ws_url)
            
            logger.info("Connected to public stream")
            
            self.is_connected = True
            self.is_running = True
            
            # Start listen key update task
            self.listen_key_update_task = asyncio.create_task(self._keep_listen_key_alive())
            
            # Start message handlers
            asyncio.create_task(self._handle_auth_messages())
            asyncio.create_task(self._handle_public_messages())
            
            logger.info("Pi42 WebSocket connected successfully")
            
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {str(e)}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Close WebSocket connections."""
        try:
            logger.info("Disconnecting from Pi42 WebSocket")
            
            self.is_running = False
            
            # Cancel listen key update task
            if self.listen_key_update_task:
                self.listen_key_update_task.cancel()
            
            # Close connections
            if self.auth_ws:
                await self.auth_ws.close()
            
            if self.public_ws:
                await self.public_ws.close()
            
            # Delete listen key
            if self.listen_key:
                delete_listen_key(self.auth_token, self.listen_key)
            
            self.is_connected = False
            
            logger.info("Disconnected from Pi42 WebSocket")
            
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
    
    async def _keep_listen_key_alive(self):
        """Keep listen key alive by updating every 30 minutes."""
        try:
            while self.is_running:
                # Wait 30 minutes
                await asyncio.sleep(30 * 60)
                
                if not self.is_running:
                    break
                
                # Update listen key
                success = update_listen_key(self.auth_token, self.listen_key)
                
                if success:
                    logger.info("Listen key updated successfully")
                else:
                    logger.error("Failed to update listen key")
                    # Reconnect if update fails
                    await self.reconnect()
                    
        except asyncio.CancelledError:
            logger.info("Listen key update task cancelled")
        except Exception as e:
            logger.error(f"Error in listen key update: {str(e)}")
    
    async def _handle_auth_messages(self):
        """Handle messages from authenticated stream."""
        try:
            while self.is_running and self.auth_ws:
                try:
                    message = await self.auth_ws.recv()
                    data = json.loads(message)
                    
                    # Route message to appropriate handler
                    event_type = data.get("e")
                    
                    if event_type == "orderUpdate":
                        await self._handle_order_update(data)
                    elif event_type == "positionUpdate":
                        await self._handle_position_update(data)
                    elif event_type == "newTrade":
                        await self._handle_trade_update(data)
                    elif event_type == "fundingFee":
                        await self._handle_funding_fee(data)
                    elif event_type == "marginCallAlert":
                        await self._handle_margin_call(data)
                    elif event_type == "liquidationAlert":
                        await self._handle_liquidation_alert(data)
                    else:
                        logger.debug(f"Unknown event type: {event_type}")
                        
                except ConnectionClosed:
                    logger.warning("Authenticated stream connection closed")
                    await self.reconnect()
                    break
                    
        except Exception as e:
            logger.error(f"Error handling auth messages: {str(e)}")
    
    async def _handle_public_messages(self):
        """Handle messages from public stream."""
        try:
            while self.is_running and self.public_ws:
                try:
                    message = await self.public_ws.recv()
                    data = json.loads(message)
                    
                    # Route message to appropriate handler
                    event_type = data.get("e")
                    
                    if event_type == "ticker":
                        await self._handle_ticker_update(data)
                    elif event_type == "depth":
                        await self._handle_depth_update(data)
                    elif event_type == "aggTrade":
                        await self._handle_agg_trade(data)
                    elif event_type == "markPrice":
                        await self._handle_mark_price(data)
                    elif event_type == "kline":
                        await self._handle_kline(data)
                    else:
                        logger.debug(f"Unknown public event: {event_type}")
                        
                except ConnectionClosed:
                    logger.warning("Public stream connection closed")
                    await self.reconnect()
                    break
                    
        except Exception as e:
            logger.error(f"Error handling public messages: {str(e)}")
    
    async def _handle_order_update(self, data: dict):
        """
        Handle order update event.
        
        Event format:
        {
            "e": "orderUpdate",
            "E": 1234567890,
            "s": "BTCUSDT",
            "o": {
                "orderId": "123456",
                "status": "FILLED",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.5,
                "price": 50000,
                "executedQty": 0.5,
                "avgPrice": 50000
            }
        }
        """
        try:
            logger.info(f"Order update: {data.get('s')} - {data.get('o', {}).get('status')}")
            
            # Transform to OpenAlgo format
            order_data = {
                "symbol": data.get("s"),
                "orderid": data.get("o", {}).get("orderId"),
                "status": data.get("o", {}).get("status"),
                "side": data.get("o", {}).get("side"),
                "quantity": data.get("o", {}).get("quantity"),
                "filled_quantity": data.get("o", {}).get("executedQty"),
                "price": data.get("o", {}).get("price"),
                "average_price": data.get("o", {}).get("avgPrice"),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            # Emit to callbacks
            await self._emit_event("order_update", order_data)
            
        except Exception as e:
            logger.error(f"Error handling order update: {str(e)}")
    
    async def _handle_position_update(self, data: dict):
        """
        Handle position update event.
        
        Event format:
        {
            "e": "positionUpdate",
            "E": 1234567890,
            "s": "BTCUSDT",
            "p": {
                "side": "LONG",
                "quantity": 0.5,
                "entryPrice": 50000,
                "markPrice": 51000,
                "liquidationPrice": 45000,
                "unrealizedPnl": 500,
                "margin": 2500,
                "leverage": 10
            }
        }
        """
        try:
            logger.info(f"Position update: {data.get('s')}")
            
            # Transform to OpenAlgo format
            position_data = {
                "symbol": data.get("s"),
                "side": data.get("p", {}).get("side"),
                "quantity": data.get("p", {}).get("quantity"),
                "entry_price": data.get("p", {}).get("entryPrice"),
                "mark_price": data.get("p", {}).get("markPrice"),
                "liquidation_price": data.get("p", {}).get("liquidationPrice"),
                "unrealized_pnl": data.get("p", {}).get("unrealizedPnl"),
                "margin": data.get("p", {}).get("margin"),
                "leverage": data.get("p", {}).get("leverage"),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            # Emit to callbacks
            await self._emit_event("position_update", position_data)
            
        except Exception as e:
            logger.error(f"Error handling position update: {str(e)}")
    
    async def _handle_trade_update(self, data: dict):
        """Handle trade execution event."""
        try:
            logger.info(f"Trade update: {data.get('s')}")
            
            trade_data = {
                "symbol": data.get("s"),
                "tradeid": data.get("t", {}).get("tradeId"),
                "orderid": data.get("t", {}).get("orderId"),
                "side": data.get("t", {}).get("side"),
                "quantity": data.get("t", {}).get("quantity"),
                "price": data.get("t", {}).get("price"),
                "commission": data.get("t", {}).get("commission"),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            await self._emit_event("trade_update", trade_data)
            
        except Exception as e:
            logger.error(f"Error handling trade update: {str(e)}")
    
    async def _handle_funding_fee(self, data: dict):
        """
        Handle funding fee event.
        
        Event format:
        {
            "e": "fundingFee",
            "E": 1234567890,
            "s": "BTCUSDT",
            "f": {
                "fundingRate": 0.0001,
                "fundingFee": -2.5,
                "positionSize": 0.5,
                "markPrice": 50000
            }
        }
        """
        try:
            logger.info(f"Funding fee: {data.get('s')} - {data.get('f', {}).get('fundingFee')}")
            
            funding_data = {
                "symbol": data.get("s"),
                "funding_rate": data.get("f", {}).get("fundingRate"),
                "funding_fee": data.get("f", {}).get("fundingFee"),
                "position_size": data.get("f", {}).get("positionSize"),
                "mark_price": data.get("f", {}).get("markPrice"),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            # Store in database
            from broker.pi42.database.master_contract_db import store_funding_rate
            store_funding_rate(
                funding_data["symbol"],
                funding_data["funding_rate"],
                funding_data["mark_price"],
                0,  # index_price not in event
                funding_data["timestamp"]
            )
            
            await self._emit_event("funding_fee", funding_data)
            
        except Exception as e:
            logger.error(f"Error handling funding fee: {str(e)}")
    
    async def _handle_margin_call(self, data: dict):
        """Handle margin call alert."""
        try:
            logger.warning(f"MARGIN CALL ALERT: {data.get('s')}")
            
            alert_data = {
                "symbol": data.get("s"),
                "margin_ratio": data.get("a", {}).get("marginRatio"),
                "maintenance_margin": data.get("a", {}).get("maintenanceMargin"),
                "current_margin": data.get("a", {}).get("currentMargin"),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            await self._emit_event("margin_call", alert_data)
            
        except Exception as e:
            logger.error(f"Error handling margin call: {str(e)}")
    
    async def _handle_liquidation_alert(self, data: dict):
        """Handle liquidation alert."""
        try:
            logger.error(f"LIQUIDATION ALERT: {data.get('s')}")
            
            alert_data = {
                "symbol": data.get("s"),
                "side": data.get("a", {}).get("side"),
                "quantity": data.get("a", {}).get("quantity"),
                "liquidation_price": data.get("a", {}).get("liquidationPrice"),
                "mark_price": data.get("a", {}).get("markPrice"),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            await self._emit_event("liquidation_alert", alert_data)
            
        except Exception as e:
            logger.error(f"Error handling liquidation alert: {str(e)}")
    
    async def _handle_ticker_update(self, data: dict):
        """Handle ticker update from public stream."""
        try:
            ticker_data = {
                "symbol": data.get("s"),
                "last_price": data.get("c"),
                "mark_price": data.get("m"),
                "index_price": data.get("i"),
                "funding_rate": data.get("r"),
                "volume": data.get("v"),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            await self._emit_event("ticker_update", ticker_data)
            
        except Exception as e:
            logger.error(f"Error handling ticker update: {str(e)}")
    
    async def _handle_depth_update(self, data: dict):
        """Handle depth update from public stream."""
        try:
            depth_data = {
                "symbol": data.get("s"),
                "bids": data.get("b", []),
                "asks": data.get("a", []),
                "timestamp": datetime.fromtimestamp(data.get("E") / 1000)
            }
            
            await self._emit_event("depth_update", depth_data)
            
        except Exception as e:
            logger.error(f"Error handling depth update: {str(e)}")
    
    async def _handle_agg_trade(self, data: dict):
        """Handle aggregated trade from public stream."""
        pass  # Implement if needed
    
    async def _handle_mark_price(self, data: dict):
        """Handle mark price update."""
        pass  # Implement if needed
    
    async def _handle_kline(self, data: dict):
        """Handle kline/candlestick update."""
        pass  # Implement if needed
    
    async def subscribe_ticker(self, symbol: str):
        """
        Subscribe to ticker updates for symbol.
        
        Args:
            symbol: Trading symbol
        """
        try:
            if not self.public_ws:
                logger.error("Public WebSocket not connected")
                return
            
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@ticker"],
                "id": int(time.time())
            }
            
            await self.public_ws.send(json.dumps(subscribe_msg))
            self.subscribed_symbols.add(symbol)
            
            logger.info(f"Subscribed to ticker: {symbol}")
            
        except Exception as e:
            logger.error(f"Error subscribing to ticker: {str(e)}")
    
    async def unsubscribe_ticker(self, symbol: str):
        """Unsubscribe from ticker updates."""
        try:
            if not self.public_ws:
                return
            
            unsubscribe_msg = {
                "method": "UNSUBSCRIBE",
                "params": [f"{symbol.lower()}@ticker"],
                "id": int(time.time())
            }
            
            await self.public_ws.send(json.dumps(unsubscribe_msg))
            self.subscribed_symbols.discard(symbol)
            
            logger.info(f"Unsubscribed from ticker: {symbol}")
            
        except Exception as e:
            logger.error(f"Error unsubscribing from ticker: {str(e)}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register callback for event type.
        
        Args:
            event_type: Event type (order_update, position_update, etc.)
            callback: Callback function
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        
        self.callbacks[event_type].append(callback)
        logger.info(f"Registered callback for {event_type}")
    
    async def _emit_event(self, event_type: str, data: dict):
        """Emit event to registered callbacks."""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for {event_type}: {str(e)}")
    
    async def reconnect(self):
        """Reconnect to WebSocket."""
        try:
            logger.info("Attempting to reconnect...")
            
            await self.disconnect()
            await asyncio.sleep(5)  # Wait before reconnecting
            await self.connect()
            
            # Resubscribe to symbols
            for symbol in self.subscribed_symbols.copy():
                await self.subscribe_ticker(symbol)
            
            logger.info("Reconnected successfully")
            
        except Exception as e:
            logger.error(f"Error reconnecting: {str(e)}")
```

## Integration with OpenAlgo WebSocket Proxy

```python
# websocket_proxy/pi42_integration.py

from broker.pi42.streaming.pi42_adapter import Pi42WebSocketAdapter

async def start_pi42_websocket(auth_token: str):
    """Start Pi42 WebSocket adapter."""
    adapter = Pi42WebSocketAdapter(auth_token)
    
    # Register callbacks
    adapter.register_callback("order_update", handle_order_update)
    adapter.register_callback("position_update", handle_position_update)
    adapter.register_callback("funding_fee", handle_funding_fee)
    adapter.register_callback("margin_call", handle_margin_call)
    adapter.register_callback("liquidation_alert", handle_liquidation_alert)
    
    # Connect
    await adapter.connect()
    
    return adapter


async def handle_order_update(data: dict):
    """Handle order update and emit to frontend."""
    from extensions import socketio
    
    socketio.emit('order_update', data)


async def handle_position_update(data: dict):
    """Handle position update and emit to frontend."""
    from extensions import socketio
    
    socketio.emit('position_update', data)


async def handle_funding_fee(data: dict):
    """Handle funding fee and emit to frontend."""
    from extensions import socketio
    
    socketio.emit('funding_fee', data)


async def handle_margin_call(data: dict):
    """Handle margin call alert."""
    from extensions import socketio
    
    # Send urgent notification
    socketio.emit('margin_call_alert', {
        'type': 'warning',
        'message': f"Margin call for {data['symbol']}",
        'data': data
    })


async def handle_liquidation_alert(data: dict):
    """Handle liquidation alert."""
    from extensions import socketio
    
    # Send critical notification
    socketio.emit('liquidation_alert', {
        'type': 'error',
        'message': f"LIQUIDATION WARNING: {data['symbol']}",
        'data': data
    })
```

## Testing

```python
async def test_websocket_connection():
    """Test WebSocket connection."""
    adapter = Pi42WebSocketAdapter(auth_token)
    await adapter.connect()
    
    assert adapter.is_connected == True
    assert adapter.listen_key is not None
    
    await adapter.disconnect()


async def test_order_updates():
    """Test order update handling."""
    adapter = Pi42WebSocketAdapter(auth_token)
    
    received_updates = []
    
    def callback(data):
        received_updates.append(data)
    
    adapter.register_callback("order_update", callback)
    await adapter.connect()
    
    # Wait for updates
    await asyncio.sleep(10)
    
    assert len(received_updates) > 0
```

## Key Features

### 1. Automatic Reconnection
- Detects connection drops
- Reconnects automatically
- Resubscribes to symbols

### 2. Listen Key Management
- Creates listen key on connect
- Updates every 30 minutes
- Deletes on disconnect

### 3. Event Routing
- Routes events to appropriate handlers
- Transforms to OpenAlgo format
- Emits to registered callbacks

### 4. Real-Time Alerts
- Margin call warnings
- Liquidation alerts
- Funding fee notifications

## Next Steps

1. Implement `pi42_adapter.py`
2. Integrate with OpenAlgo WebSocket proxy
3. Add frontend event handlers
4. Test with live data
5. Implement reconnection logic
6. Document WebSocket events
