# Pi42 Data Transformation Implementation Plan

## Overview

Data transformation is critical for converting between OpenAlgo's standardized format and Pi42's crypto futures API format. This document details all transformation logic required for seamless integration.

## Transformation Modules

### 1. File Structure

```
broker/pi42/mapping/
├── __init__.py
├── transform_data.py      # OpenAlgo → Pi42 transformations
├── order_data.py          # Pi42 → OpenAlgo transformations
└── margin_data.py         # Margin-specific transformations (optional)
```

## Implementation: `transform_data.py`

### Core Transformations

```python
"""
Pi42 Data Transformation Module

Transforms OpenAlgo format to Pi42 API format for orders and requests.
"""

from typing import Dict, Optional

from database.token_db import get_symbol_info
from utils.logging import get_logger

logger = get_logger(__name__)


def transform_order_data(data: dict) -> dict:
    """
    Transform OpenAlgo order data to Pi42 format.
    
    Args:
        data: OpenAlgo order data
            {
                "symbol": "BTCUSDT",
                "action": "BUY" | "SELL",
                "quantity": "0.5",
                "pricetype": "MARKET" | "LIMIT" | "SL" | "SL-M",
                "price": "50000",
                "trigger_price": "49000",
                "product": "ISOLATED" | "CROSS",
                "leverage": 10,
                "margin_asset": "USDT"
            }
            
    Returns:
        Pi42 order format
            {
                "placeType": "ORDER_FORM",
                "symbol": "BTCUSDT",
                "side": "BUY" | "SELL",
                "type": "MARKET" | "LIMIT" | "STOP_MARKET" | "STOP_LIMIT",
                "quantity": 0.5,
                "price": 50000,
                "stopPrice": 49000,
                "marginAsset": "USDT",
                "leverage": 10
            }
    """
    try:
        # Map order type
        order_type = map_order_type(data.get("pricetype", "MARKET"))
        
        # Build Pi42 order
        pi42_order = {
            "placeType": "ORDER_FORM",
            "symbol": data["symbol"].upper(),
            "side": data["action"].upper(),
            "type": order_type,
            "quantity": float(data["quantity"])
        }
        
        # Add price for LIMIT and STOP_LIMIT orders
        if order_type in ["LIMIT", "STOP_LIMIT"]:
            if "price" in data and data["price"]:
                pi42_order["price"] = float(data["price"])
            else:
                raise ValueError(f"Price required for {order_type} orders")
        
        # Add stop price for STOP orders
        if order_type in ["STOP_MARKET", "STOP_LIMIT"]:
            if "trigger_price" in data and data["trigger_price"]:
                pi42_order["stopPrice"] = float(data["trigger_price"])
            else:
                raise ValueError(f"Stop price required for {order_type} orders")
        
        # Add margin asset (default to USDT)
        pi42_order["marginAsset"] = data.get("margin_asset", "USDT").upper()
        
        # Add leverage (default to 1)
        pi42_order["leverage"] = int(data.get("leverage", 1))
        
        logger.debug(f"Transformed order: {pi42_order}")
        
        return pi42_order
        
    except Exception as e:
        logger.error(f"Error transforming order data: {str(e)}")
        raise


def transform_modify_order_data(data: dict) -> dict:
    """
    Transform OpenAlgo modify order data to Pi42 format.
    
    Args:
        data: Modification data
            {
                "orderid": "123456",
                "quantity": "0.6",
                "price": "51000",
                "trigger_price": "49500"
            }
            
    Returns:
        Pi42 modify format
            {
                "orderId": "123456",
                "quantity": 0.6,
                "price": 51000,
                "stopPrice": 49500
            }
    """
    try:
        pi42_modify = {
            "orderId": data["orderid"],
            "quantity": float(data["quantity"])
        }
        
        # Add price if provided
        if "price" in data and data["price"]:
            pi42_modify["price"] = float(data["price"])
        
        # Add stop price if provided
        if "trigger_price" in data and data["trigger_price"]:
            pi42_modify["stopPrice"] = float(data["trigger_price"])
        
        return pi42_modify
        
    except Exception as e:
        logger.error(f"Error transforming modify data: {str(e)}")
        raise


def map_order_type(pricetype: str) -> str:
    """
    Map OpenAlgo price type to Pi42 order type.
    
    Args:
        pricetype: OpenAlgo price type
        
    Returns:
        Pi42 order type
    """
    order_type_map = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "SL": "STOP_LIMIT",      # Stop Loss → Stop Limit
        "SL-M": "STOP_MARKET"    # Stop Loss Market → Stop Market
    }
    
    mapped_type = order_type_map.get(pricetype.upper(), "MARKET")
    logger.debug(f"Mapped order type: {pricetype} → {mapped_type}")
    
    return mapped_type


def reverse_map_order_type(pi42_type: str) -> str:
    """
    Map Pi42 order type to OpenAlgo price type.
    
    Args:
        pi42_type: Pi42 order type
        
    Returns:
        OpenAlgo price type
    """
    reverse_map = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "STOP_MARKET": "SL-M",
        "STOP_LIMIT": "SL"
    }
    
    return reverse_map.get(pi42_type.upper(), "MARKET")


def map_margin_mode(product: str) -> str:
    """
    Map OpenAlgo product to Pi42 margin mode.
    
    Args:
        product: OpenAlgo product (MIS/NRML/CNC or ISOLATED/CROSS)
        
    Returns:
        Pi42 margin mode (ISOLATED/CROSS)
    """
    # For crypto, we use margin modes instead of product types
    margin_mode_map = {
        "MIS": "ISOLATED",      # Intraday → Isolated
        "NRML": "CROSS",        # Normal → Cross
        "CNC": "CROSS",         # Delivery → Cross
        "ISOLATED": "ISOLATED",
        "CROSS": "CROSS"
    }
    
    return margin_mode_map.get(product.upper(), "ISOLATED")


def reverse_map_margin_mode(margin_mode: str) -> str:
    """
    Map Pi42 margin mode to OpenAlgo product.
    
    Args:
        margin_mode: Pi42 margin mode
        
    Returns:
        OpenAlgo product type
    """
    reverse_map = {
        "ISOLATED": "ISOLATED",
        "CROSS": "CROSS"
    }
    
    return reverse_map.get(margin_mode.upper(), "ISOLATED")


def map_order_status(pi42_status: str) -> str:
    """
    Map Pi42 order status to OpenAlgo status.
    
    Args:
        pi42_status: Pi42 order status
        
    Returns:
        OpenAlgo order status
    """
    status_map = {
        "NEW": "open",
        "PARTIALLY_FILLED": "open",
        "FILLED": "complete",
        "CANCELED": "cancelled",
        "REJECTED": "rejected",
        "EXPIRED": "cancelled"
    }
    
    return status_map.get(pi42_status.upper(), "open")


def map_side(action: str) -> str:
    """
    Map OpenAlgo action to Pi42 side.
    
    Args:
        action: OpenAlgo action (BUY/SELL)
        
    Returns:
        Pi42 side (BUY/SELL)
    """
    return action.upper()


def reverse_map_side(side: str) -> str:
    """
    Map Pi42 side to OpenAlgo action.
    
    Args:
        side: Pi42 side
        
    Returns:
        OpenAlgo action
    """
    return side.upper()


def calculate_liquidation_price(entry_price: float, leverage: int, 
                                side: str, margin_ratio: float = 0.01) -> float:
    """
    Calculate liquidation price for position.
    
    Args:
        entry_price: Entry price
        leverage: Leverage used
        side: Position side (LONG/SHORT)
        margin_ratio: Maintenance margin ratio (default 1%)
        
    Returns:
        Liquidation price
    """
    try:
        if side.upper() == "LONG":
            # Long liquidation: entry_price * (1 - 1/leverage + margin_ratio)
            liq_price = entry_price * (1 - 1/leverage + margin_ratio)
        else:
            # Short liquidation: entry_price * (1 + 1/leverage - margin_ratio)
            liq_price = entry_price * (1 + 1/leverage - margin_ratio)
        
        return round(liq_price, 2)
        
    except Exception as e:
        logger.error(f"Error calculating liquidation price: {str(e)}")
        return 0.0


def calculate_position_value(quantity: float, price: float) -> float:
    """
    Calculate position value (notional).
    
    Args:
        quantity: Position quantity
        price: Current price
        
    Returns:
        Position value
    """
    return abs(quantity) * price


def calculate_required_margin(quantity: float, price: float, leverage: int) -> float:
    """
    Calculate required margin for position.
    
    Args:
        quantity: Position quantity
        price: Entry price
        leverage: Leverage used
        
    Returns:
        Required margin
    """
    position_value = calculate_position_value(quantity, price)
    return position_value / leverage


def calculate_unrealized_pnl(quantity: float, entry_price: float, 
                             current_price: float, side: str) -> float:
    """
    Calculate unrealized PnL for position.
    
    Args:
        quantity: Position quantity
        entry_price: Entry price
        current_price: Current mark price
        side: Position side (LONG/SHORT)
        
    Returns:
        Unrealized PnL
    """
    try:
        if side.upper() == "LONG":
            pnl = quantity * (current_price - entry_price)
        else:
            pnl = quantity * (entry_price - current_price)
        
        return round(pnl, 2)
        
    except Exception as e:
        logger.error(f"Error calculating unrealized PnL: {str(e)}")
        return 0.0


def calculate_roe(pnl: float, margin: float) -> float:
    """
    Calculate Return on Equity (ROE) percentage.
    
    Args:
        pnl: Profit/Loss
        margin: Margin used
        
    Returns:
        ROE percentage
    """
    try:
        if margin == 0:
            return 0.0
        
        roe = (pnl / margin) * 100
        return round(roe, 2)
        
    except Exception as e:
        logger.error(f"Error calculating ROE: {str(e)}")
        return 0.0


def format_crypto_price(price: float, symbol: str) -> float:
    """
    Format price according to crypto precision.
    
    Args:
        price: Price to format
        symbol: Trading symbol
        
    Returns:
        Formatted price
    """
    try:
        # Get symbol info for precision
        symbol_info = get_symbol_info(symbol, "PI42")
        
        if symbol_info and hasattr(symbol_info, 'tick_size'):
            tick_size = symbol_info.tick_size
            return round(price / tick_size) * tick_size
        
        # Default precision based on symbol
        if "BTC" in symbol.upper():
            return round(price, 2)  # BTC: 2 decimals for price
        elif "ETH" in symbol.upper():
            return round(price, 2)  # ETH: 2 decimals for price
        else:
            return round(price, 4)  # Others: 4 decimals
            
    except Exception as e:
        logger.error(f"Error formatting price: {str(e)}")
        return round(price, 2)


def format_crypto_quantity(quantity: float, symbol: str) -> float:
    """
    Format quantity according to crypto precision.
    
    Args:
        quantity: Quantity to format
        symbol: Trading symbol
        
    Returns:
        Formatted quantity
    """
    try:
        # Get symbol info for precision
        symbol_info = get_symbol_info(symbol, "PI42")
        
        if symbol_info and hasattr(symbol_info, 'lotsize'):
            min_qty = symbol_info.lotsize
            return round(quantity / min_qty) * min_qty
        
        # Default precision based on symbol
        if "BTC" in symbol.upper():
            return round(quantity, 3)  # BTC: 3 decimals (0.001)
        elif "ETH" in symbol.upper():
            return round(quantity, 2)  # ETH: 2 decimals (0.01)
        else:
            return round(quantity, 1)  # Others: 1 decimal
            
    except Exception as e:
        logger.error(f"Error formatting quantity: {str(e)}")
        return round(quantity, 3)
```

## Implementation: `order_data.py`

### Response Transformations

```python
"""
Pi42 Order Data Transformation Module

Transforms Pi42 API responses to OpenAlgo format for display.
"""

from typing import Dict, List, Optional

from broker.pi42.mapping.transform_data import (
    reverse_map_order_type,
    reverse_map_side,
    reverse_map_margin_mode,
    map_order_status,
    calculate_unrealized_pnl,
    calculate_roe
)
from utils.logging import get_logger

logger = get_logger(__name__)


def map_order_data(order_data: dict) -> dict:
    """
    Transform Pi42 order response to OpenAlgo format.
    
    Args:
        order_data: Pi42 order response
        
    Returns:
        Transformed order data
    """
    try:
        if not order_data.get("success"):
            logger.warning("Order data not successful")
            return {"data": []}
        
        orders = order_data.get("data", [])
        
        if not orders:
            return {"data": []}
        
        # Transform each order
        transformed_orders = []
        for order in orders:
            transformed_order = {
                "symbol": order.get("symbol", ""),
                "exchange": "PI42",  # Crypto exchange identifier
                "action": reverse_map_side(order.get("side", "BUY")),
                "quantity": float(order.get("quantity", 0)),
                "filled_quantity": float(order.get("executedQty", 0)),
                "price": float(order.get("price", 0)),
                "average_price": float(order.get("avgPrice", 0)),
                "trigger_price": float(order.get("stopPrice", 0)),
                "pricetype": reverse_map_order_type(order.get("type", "MARKET")),
                "product": reverse_map_margin_mode(order.get("marginMode", "ISOLATED")),
                "orderid": order.get("orderId", ""),
                "order_status": map_order_status(order.get("status", "NEW")),
                "timestamp": order.get("createdAt", ""),
                "leverage": int(order.get("leverage", 1)),
                "margin_asset": order.get("marginAsset", "USDT")
            }
            transformed_orders.append(transformed_order)
        
        return {"data": transformed_orders}
        
    except Exception as e:
        logger.error(f"Error mapping order data: {str(e)}")
        return {"data": []}


def transform_order_data(orders: List[dict]) -> List[dict]:
    """
    Transform order data to standardized format for UI.
    
    Args:
        orders: List of order dictionaries
        
    Returns:
        List of transformed orders
    """
    transformed = []
    
    for order in orders:
        transformed_order = {
            "symbol": order.get("symbol", ""),
            "exchange": order.get("exchange", "PI42"),
            "action": order.get("action", ""),
            "quantity": order.get("quantity", 0),
            "price": order.get("price", 0),
            "trigger_price": order.get("trigger_price", 0),
            "pricetype": order.get("pricetype", ""),
            "product": order.get("product", ""),
            "orderid": order.get("orderid", ""),
            "order_status": order.get("order_status", ""),
            "timestamp": order.get("timestamp", ""),
            "leverage": order.get("leverage", 1),
            "margin_asset": order.get("margin_asset", "USDT")
        }
        transformed.append(transformed_order)
    
    return transformed


def calculate_order_statistics(order_data: List[dict]) -> dict:
    """
    Calculate order statistics for dashboard.
    
    Args:
        order_data: List of orders
        
    Returns:
        Statistics dictionary
    """
    stats = {
        "total_buy_orders": 0,
        "total_sell_orders": 0,
        "total_completed_orders": 0,
        "total_open_orders": 0,
        "total_rejected_orders": 0
    }
    
    for order in order_data:
        # Count by action
        if order.get("action") == "BUY":
            stats["total_buy_orders"] += 1
        elif order.get("action") == "SELL":
            stats["total_sell_orders"] += 1
        
        # Count by status
        status = order.get("order_status", "").lower()
        if status == "complete":
            stats["total_completed_orders"] += 1
        elif status == "open":
            stats["total_open_orders"] += 1
        elif status == "rejected":
            stats["total_rejected_orders"] += 1
    
    return stats


def map_position_data(position_data: dict) -> dict:
    """
    Transform Pi42 position response to OpenAlgo format.
    
    Args:
        position_data: Pi42 position response
        
    Returns:
        Transformed position data
    """
    try:
        if not position_data.get("success"):
            logger.warning("Position data not successful")
            return {"data": []}
        
        positions = position_data.get("data", [])
        
        if not positions:
            return {"data": []}
        
        # Transform each position
        transformed_positions = []
        for position in positions:
            # Calculate additional fields
            quantity = float(position.get("quantity", 0))
            entry_price = float(position.get("entryPrice", 0))
            mark_price = float(position.get("markPrice", 0))
            side = position.get("side", "LONG")
            margin = float(position.get("margin", 0))
            
            unrealized_pnl = calculate_unrealized_pnl(quantity, entry_price, mark_price, side)
            roe = calculate_roe(unrealized_pnl, margin)
            
            transformed_position = {
                "symbol": position.get("symbol", ""),
                "exchange": "PI42",
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "mark_price": mark_price,
                "liquidation_price": float(position.get("liquidationPrice", 0)),
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": float(position.get("realizedPnl", 0)),
                "margin": margin,
                "leverage": int(position.get("leverage", 1)),
                "margin_mode": position.get("marginMode", "ISOLATED"),
                "margin_asset": position.get("marginAsset", "USDT"),
                "roe": roe,
                "funding_fee": float(position.get("fundingFee", 0))
            }
            transformed_positions.append(transformed_position)
        
        return {"data": transformed_positions}
        
    except Exception as e:
        logger.error(f"Error mapping position data: {str(e)}")
        return {"data": []}


def transform_positions_data(positions: List[dict]) -> List[dict]:
    """
    Transform position data to standardized format for UI.
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        List of transformed positions
    """
    transformed = []
    
    for position in positions:
        transformed_position = {
            "symbol": position.get("symbol", ""),
            "exchange": position.get("exchange", "PI42"),
            "side": position.get("side", ""),
            "quantity": position.get("quantity", 0),
            "entry_price": position.get("entry_price", 0),
            "mark_price": position.get("mark_price", 0),
            "liquidation_price": position.get("liquidation_price", 0),
            "unrealized_pnl": position.get("unrealized_pnl", 0),
            "margin": position.get("margin", 0),
            "leverage": position.get("leverage", 1),
            "roe": position.get("roe", 0)
        }
        transformed.append(transformed_position)
    
    return transformed


def calculate_portfolio_statistics(positions: List[dict]) -> dict:
    """
    Calculate portfolio statistics for crypto positions.
    
    Args:
        positions: List of positions
        
    Returns:
        Statistics dictionary
    """
    stats = {
        "total_positions": len(positions),
        "total_margin": 0,
        "total_unrealized_pnl": 0,
        "total_realized_pnl": 0,
        "total_funding_fees": 0,
        "average_leverage": 0,
        "long_positions": 0,
        "short_positions": 0
    }
    
    if not positions:
        return stats
    
    total_leverage = 0
    
    for position in positions:
        stats["total_margin"] += position.get("margin", 0)
        stats["total_unrealized_pnl"] += position.get("unrealized_pnl", 0)
        stats["total_realized_pnl"] += position.get("realized_pnl", 0)
        stats["total_funding_fees"] += position.get("funding_fee", 0)
        total_leverage += position.get("leverage", 1)
        
        if position.get("side") == "LONG":
            stats["long_positions"] += 1
        else:
            stats["short_positions"] += 1
    
    stats["average_leverage"] = round(total_leverage / len(positions), 2)
    stats["total_margin"] = round(stats["total_margin"], 2)
    stats["total_unrealized_pnl"] = round(stats["total_unrealized_pnl"], 2)
    stats["total_realized_pnl"] = round(stats["total_realized_pnl"], 2)
    stats["total_funding_fees"] = round(stats["total_funding_fees"], 2)
    
    return stats


def map_trade_data(trade_data: dict) -> dict:
    """
    Transform Pi42 trade response to OpenAlgo format.
    
    Args:
        trade_data: Pi42 trade response
        
    Returns:
        Transformed trade data
    """
    try:
        if not trade_data.get("success"):
            logger.warning("Trade data not successful")
            return {"data": []}
        
        trades = trade_data.get("data", [])
        
        if not trades:
            return {"data": []}
        
        # Transform each trade
        transformed_trades = []
        for trade in trades:
            transformed_trade = {
                "symbol": trade.get("symbol", ""),
                "exchange": "PI42",
                "action": reverse_map_side(trade.get("side", "BUY")),
                "quantity": float(trade.get("quantity", 0)),
                "price": float(trade.get("price", 0)),
                "trade_value": float(trade.get("quantity", 0)) * float(trade.get("price", 0)),
                "orderid": trade.get("orderId", ""),
                "tradeid": trade.get("tradeId", ""),
                "timestamp": trade.get("timestamp", ""),
                "commission": float(trade.get("commission", 0)),
                "commission_asset": trade.get("commissionAsset", "USDT")
            }
            transformed_trades.append(transformed_trade)
        
        return {"data": transformed_trades}
        
    except Exception as e:
        logger.error(f"Error mapping trade data: {str(e)}")
        return {"data": []}


def transform_tradebook_data(trades: List[dict]) -> List[dict]:
    """
    Transform trade data to standardized format for UI.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        List of transformed trades
    """
    transformed = []
    
    for trade in trades:
        transformed_trade = {
            "symbol": trade.get("symbol", ""),
            "exchange": trade.get("exchange", "PI42"),
            "action": trade.get("action", ""),
            "quantity": trade.get("quantity", 0),
            "price": trade.get("price", 0),
            "trade_value": trade.get("trade_value", 0),
            "orderid": trade.get("orderid", ""),
            "timestamp": trade.get("timestamp", "")
        }
        transformed.append(transformed_trade)
    
    return transformed
```

## Testing

```python
def test_transform_order_data():
    """Test order data transformation."""
    openalgo_data = {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "quantity": "0.5",
        "pricetype": "LIMIT",
        "price": "50000",
        "leverage": 10
    }
    
    pi42_data = transform_order_data(openalgo_data)
    
    assert pi42_data["symbol"] == "BTCUSDT"
    assert pi42_data["side"] == "BUY"
    assert pi42_data["type"] == "LIMIT"
    assert pi42_data["quantity"] == 0.5
    assert pi42_data["leverage"] == 10


def test_calculate_liquidation_price():
    """Test liquidation price calculation."""
    # Long position
    liq_price = calculate_liquidation_price(50000, 10, "LONG")
    assert liq_price < 50000
    
    # Short position
    liq_price = calculate_liquidation_price(50000, 10, "SHORT")
    assert liq_price > 50000


def test_calculate_unrealized_pnl():
    """Test unrealized PnL calculation."""
    # Long position profit
    pnl = calculate_unrealized_pnl(0.5, 50000, 51000, "LONG")
    assert pnl == 500
    
    # Short position profit
    pnl = calculate_unrealized_pnl(0.5, 50000, 49000, "SHORT")
    assert pnl == 500
```

## Key Transformation Rules

### 1. Order Type Mapping
- MARKET → MARKET (no change)
- LIMIT → LIMIT (no change)
- SL → STOP_LIMIT (stop loss with limit price)
- SL-M → STOP_MARKET (stop loss at market)

### 2. Product/Margin Mode
- MIS → ISOLATED (intraday isolated margin)
- NRML → CROSS (normal cross margin)
- CNC → CROSS (delivery cross margin)

### 3. Precision Handling
- BTC: 3 decimals for quantity, 2 for price
- ETH: 2 decimals for quantity, 2 for price
- Always respect tick size and lot size

### 4. Position Calculations
- Liquidation price depends on leverage and side
- Unrealized PnL calculated from mark price
- ROE = (PnL / Margin) * 100

## Next Steps

1. Implement `transform_data.py` with all functions
2. Implement `order_data.py` with all transformations
3. Add comprehensive unit tests
4. Test with various order types and symbols
5. Validate precision handling
6. Document all transformation rules
