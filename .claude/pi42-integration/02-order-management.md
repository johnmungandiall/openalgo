# Pi42 Order Management Implementation Plan

## Overview

Pi42 order management differs significantly from stock trading due to crypto futures-specific features like leverage, margin modes, stop orders, and split TP/SL. This document details the complete order management implementation.

## Order Types

### 1. Supported Order Types

| Order Type | Description | Required Fields |
|-----------|-------------|-----------------|
| **MARKET** | Execute at best available price | symbol, side, quantity |
| **LIMIT** | Execute at specified price or better | symbol, side, quantity, price |
| **STOP_MARKET** | Market order triggered at stop price | symbol, side, quantity, stopPrice |
| **STOP_LIMIT** | Limit order triggered at stop price | symbol, side, quantity, price, stopPrice |

### 2. Order Type Mapping

```python
# OpenAlgo → Pi42
ORDER_TYPE_MAP = {
    "MARKET": "MARKET",
    "LIMIT": "LIMIT",
    "SL": "STOP_LIMIT",      # Stop Loss → Stop Limit
    "SL-M": "STOP_MARKET"    # Stop Loss Market → Stop Market
}

# Pi42 → OpenAlgo (reverse)
REVERSE_ORDER_TYPE_MAP = {
    "MARKET": "MARKET",
    "LIMIT": "LIMIT",
    "STOP_MARKET": "SL-M",
    "STOP_LIMIT": "SL"
}
```

## File Structure

```
broker/pi42/api/
├── __init__.py
├── auth_api.py          # Already covered
├── order_api.py         # Main order management (THIS FILE)
├── data.py              # Market data
└── funds.py             # Wallet/balance
```

## Implementation: `broker/pi42/api/order_api.py`

### Core Functions

#### 1. Place Order

```python
"""
Pi42 Order Management API

Handles order placement, modification, cancellation, and position management
for crypto futures trading.
"""

import json
import time
from typing import Dict, List, Optional, Tuple

from broker.pi42.api.auth_api import create_auth_instance
from broker.pi42.mapping.transform_data import transform_order_data
from database.token_db import get_token
from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)


def place_order_api(data: dict, auth_token: str) -> Tuple[Optional[object], dict, Optional[str]]:
    """
    Place order on Pi42 exchange.
    
    Args:
        data: Order data in OpenAlgo format
            {
                "symbol": "BTCUSDT",
                "action": "BUY" | "SELL",
                "quantity": 0.5,
                "pricetype": "MARKET" | "LIMIT" | "SL" | "SL-M",
                "price": 50000,  # Required for LIMIT/SL
                "trigger_price": 49000,  # Required for SL/SL-M
                "product": "ISOLATED" | "CROSS",  # Margin mode
                "leverage": 10,  # Optional, default from settings
                "margin_asset": "USDT" | "INR"  # Optional
            }
        auth_token: Authentication token
        
    Returns:
        Tuple of (response, response_data, orderid)
    """
    try:
        logger.info(f"Placing Pi42 order: {data['symbol']} {data['action']} {data['quantity']}")
        
        # Create auth instance
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Transform OpenAlgo data to Pi42 format
        pi42_data = transform_order_data(data)
        
        logger.debug(f"Transformed order data: {pi42_data}")
        
        # Sign request
        headers, body = auth.sign_request("POST", "/v1/order/place-order", body=pi42_data)
        
        # Make API request
        response = client.post(
            f"{auth.base_url}/v1/order/place-order",
            headers=headers,
            json=body,
            timeout=10
        )
        
        logger.info(f"Pi42 order response status: {response.status_code}")
        logger.debug(f"Pi42 order response: {response.text}")
        
        response_data = response.json()
        
        # Extract order ID
        orderid = None
        if response_data.get("success"):
            orderid = response_data.get("data", {}).get("orderId")
            logger.info(f"Order placed successfully: {orderid}")
        else:
            error_msg = response_data.get("message", "Unknown error")
            logger.error(f"Order placement failed: {error_msg}")
        
        # Add status attribute for compatibility
        response.status = response.status_code
        
        return response, response_data, orderid
        
    except Exception as e:
        logger.error(f"Error placing Pi42 order: {str(e)}")
        return None, {"success": False, "message": str(e)}, None


def place_smartorder_api(data: dict, auth_token: str) -> Tuple[Optional[object], dict, Optional[str]]:
    """
    Place smart order that adjusts position to target size.
    
    For crypto futures, smart order:
    1. Gets current position
    2. Calculates required action to reach target position_size
    3. Places order to adjust position
    
    Args:
        data: Order data with position_size field
        auth_token: Authentication token
        
    Returns:
        Tuple of (response, response_data, orderid)
    """
    try:
        symbol = data.get("symbol")
        target_position = float(data.get("position_size", 0))
        
        logger.info(f"Smart order for {symbol}, target position: {target_position}")
        
        # Get current position
        current_position = get_open_position(symbol, auth_token)
        
        logger.info(f"Current position: {current_position}")
        
        # Calculate required action
        position_diff = target_position - current_position
        
        if abs(position_diff) < 0.0001:  # Negligible difference
            return None, {
                "success": True,
                "message": "Position already at target size"
            }, None
        
        # Determine action and quantity
        if position_diff > 0:
            action = "BUY"
            quantity = abs(position_diff)
        else:
            action = "SELL"
            quantity = abs(position_diff)
        
        # Prepare order data
        order_data = data.copy()
        order_data["action"] = action
        order_data["quantity"] = str(quantity)
        
        logger.info(f"Smart order: {action} {quantity} {symbol}")
        
        # Place order
        return place_order_api(order_data, auth_token)
        
    except Exception as e:
        logger.error(f"Error in smart order: {str(e)}")
        return None, {"success": False, "message": str(e)}, None


def get_open_position(symbol: str, auth_token: str) -> float:
    """
    Get current open position quantity for symbol.
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        auth_token: Authentication token
        
    Returns:
        Net position quantity (positive for long, negative for short)
    """
    try:
        positions_data = get_positions(auth_token, status="OPEN")
        
        if not positions_data.get("success"):
            return 0.0
        
        positions = positions_data.get("data", [])
        
        for position in positions:
            if position.get("symbol") == symbol:
                side = position.get("side")
                quantity = float(position.get("quantity", 0))
                
                # Return signed quantity (positive for LONG, negative for SHORT)
                return quantity if side == "LONG" else -quantity
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error getting open position: {str(e)}")
        return 0.0
```

#### 2. Modify Order

```python
def modify_order(data: dict, auth_token: str) -> Tuple[dict, int]:
    """
    Modify existing order.
    
    Pi42 allows modifying:
    - Quantity
    - Price (for LIMIT orders)
    - Stop price (for STOP orders)
    
    Args:
        data: Modification data
            {
                "orderid": "123456",
                "symbol": "BTCUSDT",
                "quantity": 0.6,  # New quantity
                "price": 51000,   # New price (optional)
                "trigger_price": 49500  # New stop price (optional)
            }
        auth_token: Authentication token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        logger.info(f"Modifying Pi42 order: {data.get('orderid')}")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Build modification payload
        modify_payload = {
            "orderId": data["orderid"],
            "quantity": float(data["quantity"])
        }
        
        # Add price if provided
        if "price" in data and data["price"]:
            modify_payload["price"] = float(data["price"])
        
        # Add stop price if provided
        if "trigger_price" in data and data["trigger_price"]:
            modify_payload["stopPrice"] = float(data["trigger_price"])
        
        logger.debug(f"Modify payload: {modify_payload}")
        
        # Sign request
        headers, body = auth.sign_request("PATCH", "/v1/order/edit-order", body=modify_payload)
        
        # Make API request
        response = client.patch(
            f"{auth.base_url}/v1/order/edit-order",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            logger.info(f"Order modified successfully: {data['orderid']}")
            return {
                "status": "success",
                "orderid": data["orderid"]
            }, 200
        else:
            error_msg = response_data.get("message", "Modification failed")
            logger.error(f"Order modification failed: {error_msg}")
            return {
                "status": "error",
                "message": error_msg
            }, response.status_code
            
    except Exception as e:
        logger.error(f"Error modifying order: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
```

#### 3. Cancel Order

```python
def cancel_order(orderid: str, auth_token: str) -> Tuple[dict, int]:
    """
    Cancel order by order ID.
    
    Args:
        orderid: Order ID to cancel
        auth_token: Authentication token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        logger.info(f"Cancelling Pi42 order: {orderid}")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Build cancel payload
        cancel_payload = {"orderId": orderid}
        
        # Sign request
        headers, body = auth.sign_request("DELETE", "/v1/order/delete-order", body=cancel_payload)
        
        # Make API request
        response = client.delete(
            f"{auth.base_url}/v1/order/delete-order",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            logger.info(f"Order cancelled successfully: {orderid}")
            return {"status": "success", "orderid": orderid}, 200
        else:
            error_msg = response_data.get("message", "Cancellation failed")
            logger.error(f"Order cancellation failed: {error_msg}")
            return {"status": "error", "message": error_msg}, response.status_code
            
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


def cancel_all_orders_api(data: dict, auth_token: str) -> Tuple[List[str], List[str]]:
    """
    Cancel all open orders.
    
    Args:
        data: Request data (may contain symbol filter)
        auth_token: Authentication token
        
    Returns:
        Tuple of (canceled_orders, failed_cancellations)
    """
    try:
        logger.info("Cancelling all Pi42 orders")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Get symbol filter if provided
        symbol = data.get("symbol")
        
        # Build payload
        cancel_payload = {}
        if symbol:
            cancel_payload["symbol"] = symbol
        
        # Sign request
        headers, body = auth.sign_request("DELETE", "/v1/order/cancel-all-orders", body=cancel_payload)
        
        # Make API request
        response = client.delete(
            f"{auth.base_url}/v1/order/cancel-all-orders",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            # Pi42 returns list of cancelled order IDs
            cancelled = response_data.get("data", {}).get("cancelledOrders", [])
            failed = response_data.get("data", {}).get("failedOrders", [])
            
            logger.info(f"Cancelled {len(cancelled)} orders, {len(failed)} failed")
            return cancelled, failed
        else:
            logger.error("Cancel all orders failed")
            return [], []
            
    except Exception as e:
        logger.error(f"Error cancelling all orders: {str(e)}")
        return [], []
```

#### 4. Get Order Book

```python
def get_order_book(auth_token: str) -> dict:
    """
    Get all open orders.
    
    Returns:
        Dictionary with order data
    """
    try:
        logger.info("Fetching Pi42 order book")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Sign request
        headers, params = auth.sign_request("GET", "/v1/order/open-orders")
        
        # Build URL with query params
        url = f"{auth.base_url}/v1/order/open-orders"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"
        
        # Make API request
        response = client.get(url, headers=headers, timeout=10)
        
        response_data = response.json()
        
        logger.info(f"Fetched {len(response_data.get('data', []))} open orders")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error fetching order book: {str(e)}")
        return {"success": False, "message": str(e), "data": []}


def get_order_history(auth_token: str, symbol: Optional[str] = None, 
                      limit: int = 100) -> dict:
    """
    Get order history.
    
    Args:
        auth_token: Authentication token
        symbol: Filter by symbol (optional)
        limit: Number of orders to fetch
        
    Returns:
        Dictionary with order history
    """
    try:
        logger.info(f"Fetching Pi42 order history (limit: {limit})")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Build query params
        query_params = {"limit": limit}
        if symbol:
            query_params["symbol"] = symbol
        
        # Sign request
        headers, params = auth.sign_request("GET", "/v1/order/order-history", params=query_params)
        
        # Build URL
        url = f"{auth.base_url}/v1/order/order-history"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"
        
        # Make API request
        response = client.get(url, headers=headers, timeout=10)
        
        response_data = response.json()
        
        logger.info(f"Fetched {len(response_data.get('data', []))} historical orders")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error fetching order history: {str(e)}")
        return {"success": False, "message": str(e), "data": []}
```

#### 5. Get Positions

```python
def get_positions(auth_token: str, status: str = "OPEN") -> dict:
    """
    Get positions.
    
    Args:
        auth_token: Authentication token
        status: Position status - "OPEN", "CLOSED", or "LIQUIDATED"
        
    Returns:
        Dictionary with position data
    """
    try:
        logger.info(f"Fetching Pi42 positions (status: {status})")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Sign request
        headers, params = auth.sign_request("GET", f"/v1/positions/{status}")
        
        # Build URL
        url = f"{auth.base_url}/v1/positions/{status}"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"
        
        # Make API request
        response = client.get(url, headers=headers, timeout=10)
        
        response_data = response.json()
        
        logger.info(f"Fetched {len(response_data.get('data', []))} positions")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        return {"success": False, "message": str(e), "data": []}


def get_trade_book(auth_token: str) -> dict:
    """
    Get trade book (executed trades).
    
    Note: Pi42 doesn't have a separate trade book endpoint.
    Trades are included in order history with status "FILLED".
    
    Returns:
        Dictionary with trade data
    """
    try:
        logger.info("Fetching Pi42 trade book")
        
        # Get order history and filter for filled orders
        order_history = get_order_history(auth_token, limit=500)
        
        if not order_history.get("success"):
            return order_history
        
        # Filter for filled orders
        trades = [
            order for order in order_history.get("data", [])
            if order.get("status") == "FILLED"
        ]
        
        logger.info(f"Fetched {len(trades)} trades")
        
        return {
            "success": True,
            "data": trades
        }
        
    except Exception as e:
        logger.error(f"Error fetching trade book: {str(e)}")
        return {"success": False, "message": str(e), "data": []}
```

#### 6. Close All Positions

```python
def close_all_positions(current_api_key: str, auth_token: str) -> Tuple[dict, int]:
    """
    Close all open positions.
    
    Args:
        current_api_key: API key (for logging)
        auth_token: Authentication token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        logger.info("Closing all Pi42 positions")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Sign request
        headers, body = auth.sign_request("DELETE", "/v1/positions/close-all-positions")
        
        # Make API request
        response = client.delete(
            f"{auth.base_url}/v1/positions/close-all-positions",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            closed_count = len(response_data.get("data", []))
            logger.info(f"Closed {closed_count} positions")
            return {
                "status": "success",
                "message": f"Closed {closed_count} positions"
            }, 200
        else:
            error_msg = response_data.get("message", "Failed to close positions")
            logger.error(f"Close all positions failed: {error_msg}")
            return {"status": "error", "message": error_msg}, response.status_code
            
    except Exception as e:
        logger.error(f"Error closing all positions: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
```

### Advanced Features

#### 7. Leverage Management

```python
def set_leverage(symbol: str, leverage: int, auth_token: str) -> Tuple[dict, int]:
    """
    Set leverage for symbol.
    
    Args:
        symbol: Trading symbol
        leverage: Leverage value (1-25)
        auth_token: Authentication token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        logger.info(f"Setting leverage for {symbol}: {leverage}x")
        
        if not 1 <= leverage <= 25:
            return {"status": "error", "message": "Leverage must be between 1 and 25"}, 400
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Build payload
        payload = {
            "symbol": symbol,
            "leverage": leverage
        }
        
        # Sign request
        headers, body = auth.sign_request("POST", "/v1/exchange/update/preference", body=payload)
        
        # Make API request
        response = client.post(
            f"{auth.base_url}/v1/exchange/update/preference",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            logger.info(f"Leverage set successfully: {leverage}x")
            return {"status": "success", "leverage": leverage}, 200
        else:
            error_msg = response_data.get("message", "Failed to set leverage")
            logger.error(f"Set leverage failed: {error_msg}")
            return {"status": "error", "message": error_msg}, response.status_code
            
    except Exception as e:
        logger.error(f"Error setting leverage: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
```

#### 8. Margin Management

```python
def add_margin(symbol: str, amount: float, margin_asset: str, auth_token: str) -> Tuple[dict, int]:
    """
    Add margin to position.
    
    Args:
        symbol: Trading symbol
        amount: Amount to add
        margin_asset: Asset to use (USDT/INR)
        auth_token: Authentication token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        logger.info(f"Adding margin to {symbol}: {amount} {margin_asset}")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Build payload
        payload = {
            "symbol": symbol,
            "amount": amount,
            "marginAsset": margin_asset
        }
        
        # Sign request
        headers, body = auth.sign_request("POST", "/v1/order/add-margin", body=payload)
        
        # Make API request
        response = client.post(
            f"{auth.base_url}/v1/order/add-margin",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            logger.info("Margin added successfully")
            return {"status": "success"}, 200
        else:
            error_msg = response_data.get("message", "Failed to add margin")
            logger.error(f"Add margin failed: {error_msg}")
            return {"status": "error", "message": error_msg}, response.status_code
            
    except Exception as e:
        logger.error(f"Error adding margin: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


def reduce_margin(symbol: str, amount: float, auth_token: str) -> Tuple[dict, int]:
    """
    Reduce margin from position.
    
    Args:
        symbol: Trading symbol
        amount: Amount to reduce
        auth_token: Authentication token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        logger.info(f"Reducing margin from {symbol}: {amount}")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Build payload
        payload = {
            "symbol": symbol,
            "amount": amount
        }
        
        # Sign request
        headers, body = auth.sign_request("POST", "/v1/order/reduce-margin", body=payload)
        
        # Make API request
        response = client.post(
            f"{auth.base_url}/v1/order/reduce-margin",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            logger.info("Margin reduced successfully")
            return {"status": "success"}, 200
        else:
            error_msg = response_data.get("message", "Failed to reduce margin")
            logger.error(f"Reduce margin failed: {error_msg}")
            return {"status": "error", "message": error_msg}, response.status_code
            
    except Exception as e:
        logger.error(f"Error reducing margin: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
```

#### 9. Split TP/SL

```python
def set_split_tp_sl(symbol: str, tp_levels: List[dict], sl_levels: List[dict], 
                    auth_token: str) -> Tuple[dict, int]:
    """
    Set split take-profit and stop-loss levels.
    
    Args:
        symbol: Trading symbol
        tp_levels: List of TP levels
            [{"price": 52000, "quantity": 0.2}, {"price": 53000, "quantity": 0.3}]
        sl_levels: List of SL levels
            [{"price": 48000, "quantity": 0.5}]
        auth_token: Authentication token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        logger.info(f"Setting split TP/SL for {symbol}")
        logger.debug(f"TP levels: {tp_levels}, SL levels: {sl_levels}")
        
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        # Build payload
        payload = {
            "symbol": symbol,
            "takeProfitLevels": tp_levels,
            "stopLossLevels": sl_levels
        }
        
        # Sign request
        headers, body = auth.sign_request("POST", "/v2/order/split-tp-sl", body=payload)
        
        # Make API request
        response = client.post(
            f"{auth.base_url}/v2/order/split-tp-sl",
            headers=headers,
            json=body,
            timeout=10
        )
        
        response_data = response.json()
        
        if response_data.get("success"):
            logger.info("Split TP/SL set successfully")
            return {"status": "success"}, 200
        else:
            error_msg = response_data.get("message", "Failed to set split TP/SL")
            logger.error(f"Set split TP/SL failed: {error_msg}")
            return {"status": "error", "message": error_msg}, response.status_code
            
    except Exception as e:
        logger.error(f"Error setting split TP/SL: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
```

## Testing

```python
def test_place_order():
    """Test order placement."""
    data = {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "quantity": "0.001",
        "pricetype": "MARKET",
        "product": "ISOLATED",
        "leverage": 5
    }
    
    response, response_data, orderid = place_order_api(data, auth_token)
    assert response_data.get("success") == True
    assert orderid is not None


def test_cancel_order():
    """Test order cancellation."""
    response_dict, status_code = cancel_order("test_order_id", auth_token)
    assert status_code in [200, 404]  # 404 if order not found


def test_get_positions():
    """Test position fetching."""
    positions = get_positions(auth_token, "OPEN")
    assert positions.get("success") == True
    assert isinstance(positions.get("data"), list)
```

## Next Steps

1. Implement `order_api.py` with all functions
2. Create `transform_data.py` for data transformations
3. Implement `order_data.py` for response transformations
4. Add comprehensive error handling
5. Test with Pi42 sandbox/testnet
6. Document all order types and features
