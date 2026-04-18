# Phase 2: Core Trading Features (Week 3-4)

**Goal:** Implement essential crypto trading features

**Prerequisites:**
- Phase 1 completed (foundation and basic integration)
- Basic orders working (MARKET, LIMIT)
- Market data accessible

---

## Week 3: Advanced Orders & Positions

### Day 1-2: Stop Orders

#### Step 1.1: Extend Order API for STOP Orders

**File:** `broker/pi42/api/order_api.py` (extend existing)

Add these functions:

```python
def place_stop_order(
    symbol: str,
    side: str,
    quantity: float,
    stop_price: float,
    order_type: str,  # 'STOP_MARKET' or 'STOP_LIMIT'
    limit_price: Optional[float] = None,
    leverage: int = 1,
    margin_mode: str = 'ISOLATED',
    margin_asset: str = 'USDT',
    auth_token: str = None
) -> Tuple[Dict, int]:
    """
    Place STOP order on Pi42.
    
    Args:
        symbol: Trading symbol
        side: BUY or SELL
        quantity: Order quantity
        stop_price: Trigger price
        order_type: STOP_MARKET or STOP_LIMIT
        limit_price: Limit price (required for STOP_LIMIT)
        leverage: Leverage multiplier
        margin_mode: ISOLATED or CROSS
        margin_asset: USDT or INR
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Build order data
        order_data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'stopPrice': stop_price,
            'leverage': leverage,
            'marginMode': margin_mode,
            'marginAsset': margin_asset
        }
        
        # Add limit price for STOP_LIMIT
        if order_type == 'STOP_LIMIT':
            if not limit_price:
                return {
                    'status': 'error',
                    'message': 'Limit price required for STOP_LIMIT orders'
                }, 400
            order_data['price'] = limit_price
        
        # Rate limit check
        rate_limiter.wait_if_needed('place_order')
        
        # Sign and send request
        endpoint = '/v1/order/place-order'
        headers, body = auth.sign_request('POST', endpoint, body=order_data)
        
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'status': 'success',
                'orderid': result.get('orderId', ''),
                'message': f'{order_type} order placed successfully'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Order failed: {response.text}"
            }, response.status_code
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def modify_stop_order(
    order_id: str,
    stop_price: Optional[float] = None,
    limit_price: Optional[float] = None,
    quantity: Optional[float] = None,
    auth_token: str = None
) -> Tuple[Dict, int]:
    """
    Modify existing STOP order.
    
    Args:
        order_id: Order ID to modify
        stop_price: New stop price
        limit_price: New limit price
        quantity: New quantity
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Build modification data
        modify_data = {'orderId': order_id}
        
        if stop_price:
            modify_data['stopPrice'] = stop_price
        if limit_price:
            modify_data['price'] = limit_price
        if quantity:
            modify_data['quantity'] = quantity
        
        # Sign and send request
        endpoint = '/v1/order/modify-order'
        headers, body = auth.sign_request('POST', endpoint, body=modify_data)
        
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            return {
                'status': 'success',
                'orderid': order_id,
                'message': 'Order modified successfully'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Modify failed: {response.text}"
            }, response.status_code
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500
```

#### Step 1.2: Update Transform Module for STOP Orders

**File:** `broker/pi42/mapping/transform_data.py` (update existing)

Update the `transform_order_data` function:

```python
def transform_order_data(data: Dict) -> Dict:
    """
    Transform OpenAlgo order data to Pi42 format.
    
    Args:
        data: OpenAlgo order data
        
    Returns:
        Pi42 order data
    """
    # Map order type
    order_type_map = {
        'MARKET': 'MARKET',
        'LIMIT': 'LIMIT',
        'SL': 'STOP_LIMIT',
        'SL-M': 'STOP_MARKET'
    }
    
    pi42_data = {
        'symbol': data['symbol'],
        'side': data['action'],  # BUY or SELL
        'type': order_type_map.get(data['pricetype'], 'MARKET'),
        'quantity': float(data['quantity'])
    }
    
    # Add price for LIMIT and STOP_LIMIT orders
    if data['pricetype'] in ['LIMIT', 'SL']:
        pi42_data['price'] = float(data['price'])
    
    # Add stop price for STOP orders
    if data['pricetype'] in ['SL', 'SL-M']:
        # Use trigger_price if available, otherwise use price
        stop_price = data.get('trigger_price') or data.get('stoploss') or data.get('price')
        if stop_price:
            pi42_data['stopPrice'] = float(stop_price)
        else:
            raise ValueError("Stop price required for STOP orders")
    
    # Add crypto-specific fields
    pi42_data['leverage'] = int(data.get('leverage', 1))
    pi42_data['marginMode'] = data.get('margin_mode', 'ISOLATED')
    pi42_data['marginAsset'] = data.get('margin_asset', 'USDT')
    
    # Validate quantity against contract specs
    from broker.pi42.database.master_contract_db import get_contract_info
    contract = get_contract_info(data['symbol'])
    
    if contract:
        # Format to correct precision
        pi42_data['quantity'] = format_crypto_quantity(
            pi42_data['quantity'],
            contract['quantity_precision']
        )
        
        # Format prices to correct precision
        if 'price' in pi42_data:
            pi42_data['price'] = format_crypto_price(
                pi42_data['price'],
                contract['price_precision']
            )
        
        if 'stopPrice' in pi42_data:
            pi42_data['stopPrice'] = format_crypto_price(
                pi42_data['stopPrice'],
                contract['price_precision']
            )
        
        # Validate quantity range
        if pi42_data['quantity'] < contract['min_quantity']:
            raise ValueError(f"Quantity below minimum: {contract['min_quantity']}")
        if pi42_data['quantity'] > contract['max_quantity']:
            raise ValueError(f"Quantity above maximum: {contract['max_quantity']}")
    
    return pi42_data
```

#### Step 1.3: Test STOP Orders

**File:** `test/test_pi42_stop_orders.py`

```python
"""Test Pi42 STOP orders."""

import os
from broker.pi42.api.order_api import place_stop_order, modify_stop_order
from broker.pi42.api.data import BrokerData
from utils.encryption import encrypt_token


def test_stop_market_order():
    """Test STOP_MARKET order."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    # Get current price
    data = BrokerData(auth_token)
    quotes = data.get_quotes('BTCUSDT')
    current_price = quotes['ltp']
    
    # Place STOP_MARKET order 5% below current price
    stop_price = current_price * 0.95
    
    result, status = place_stop_order(
        symbol='BTCUSDT',
        side='SELL',
        quantity=0.001,
        stop_price=stop_price,
        order_type='STOP_MARKET',
        leverage=1,
        margin_mode='ISOLATED',
        margin_asset='USDT',
        auth_token=auth_token
    )
    
    print(f"STOP_MARKET Order:")
    print(f"  Current Price: {current_price}")
    print(f"  Stop Price: {stop_price}")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    assert status == 200
    assert result['status'] == 'success'
    
    return result['orderid']


def test_stop_limit_order():
    """Test STOP_LIMIT order."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    # Get current price
    data = BrokerData(auth_token)
    quotes = data.get_quotes('BTCUSDT')
    current_price = quotes['ltp']
    
    # Place STOP_LIMIT order
    stop_price = current_price * 1.05  # 5% above
    limit_price = current_price * 1.06  # 6% above
    
    result, status = place_stop_order(
        symbol='BTCUSDT',
        side='BUY',
        quantity=0.001,
        stop_price=stop_price,
        order_type='STOP_LIMIT',
        limit_price=limit_price,
        leverage=1,
        margin_mode='ISOLATED',
        margin_asset='USDT',
        auth_token=auth_token
    )
    
    print(f"\nSTOP_LIMIT Order:")
    print(f"  Current Price: {current_price}")
    print(f"  Stop Price: {stop_price}")
    print(f"  Limit Price: {limit_price}")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    assert status == 200
    assert result['status'] == 'success'
    
    return result['orderid']


if __name__ == '__main__':
    print("Testing STOP orders...")
    
    stop_market_id = test_stop_market_order()
    stop_limit_id = test_stop_limit_order()
    
    print(f"\n✓ STOP orders placed:")
    print(f"  STOP_MARKET: {stop_market_id}")
    print(f"  STOP_LIMIT: {stop_limit_id}")
    print("\nNote: Cancel manually if needed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_stop_orders.py -v -s
```

---

### Day 3-4: Position Management

#### Step 2.1: Create Position API Module

**File:** `broker/pi42/api/position_api.py` (create new)

```python
"""Pi42 position management API."""

import requests
from typing import Dict, List, Tuple
from broker.pi42.api.auth_api import create_auth_instance


def get_positions(auth_token: str) -> Tuple[Dict, int]:
    """
    Get all open positions.
    
    Args:
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Sign request
        endpoint = '/v1/position/open-positions'
        headers, _ = auth.sign_request('GET', endpoint)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f"Failed to get positions: {response.text}"
            }, response.status_code
        
        positions = response.json()
        
        # Transform to OpenAlgo format
        from broker.pi42.mapping.position_data import map_position_data
        transformed = [map_position_data(pos) for pos in positions]
        
        return {
            'status': 'success',
            'data': transformed
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def close_position(symbol: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Close position for symbol.
    
    Args:
        symbol: Trading symbol
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Get current position
        positions_result, status = get_positions(auth_token)
        if status != 200:
            return positions_result, status
        
        # Find position for symbol
        position = None
        for pos in positions_result['data']:
            if pos['symbol'] == symbol:
                position = pos
                break
        
        if not position:
            return {
                'status': 'error',
                'message': f"No open position for {symbol}"
            }, 404
        
        # Place opposite order to close
        from broker.pi42.api.order_api import place_order_api
        
        close_order = {
            'symbol': symbol,
            'action': 'SELL' if position['side'] == 'LONG' else 'BUY',
            'quantity': str(abs(position['quantity'])),
            'pricetype': 'MARKET',
            'leverage': position.get('leverage', 1),
            'margin_mode': position.get('margin_mode', 'ISOLATED'),
            'margin_asset': position.get('margin_asset', 'USDT')
        }
        
        return place_order_api(close_order, auth_token)
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def calculate_position_pnl(position: Dict, mark_price: float) -> Dict:
    """
    Calculate position PnL and metrics.
    
    Args:
        position: Position data
        mark_price: Current mark price
        
    Returns:
        Dictionary with PnL calculations
    """
    entry_price = float(position['entry_price'])
    quantity = float(position['quantity'])
    leverage = int(position.get('leverage', 1))
    side = position['side']
    
    # Calculate unrealized PnL
    if side == 'LONG':
        unrealized_pnl = (mark_price - entry_price) * quantity
    else:  # SHORT
        unrealized_pnl = (entry_price - mark_price) * quantity
    
    # Calculate margin
    margin = (entry_price * quantity) / leverage
    
    # Calculate ROE (Return on Equity)
    roe = (unrealized_pnl / margin) * 100 if margin > 0 else 0
    
    # Calculate liquidation price
    from broker.pi42.mapping.transform_data import calculate_liquidation_price
    liquidation_price = calculate_liquidation_price(entry_price, leverage, side)
    
    return {
        'unrealized_pnl': round(unrealized_pnl, 2),
        'margin': round(margin, 2),
        'roe': round(roe, 2),
        'liquidation_price': round(liquidation_price, 2),
        'mark_price': mark_price
    }
```

#### Step 2.2: Create Position Data Mapping

**File:** `broker/pi42/mapping/position_data.py` (create new)

```python
"""Map Pi42 position data to OpenAlgo format."""

from typing import Dict


def map_position_data(position: Dict) -> Dict:
    """
    Map Pi42 position to OpenAlgo format.
    
    Args:
        position: Pi42 position data
        
    Returns:
        OpenAlgo position data
    """
    # Determine side from position amount
    quantity = float(position['positionAmt'])
    side = 'LONG' if quantity > 0 else 'SHORT'
    
    # Calculate metrics
    entry_price = float(position['entryPrice'])
    mark_price = float(position['markPrice'])
    leverage = int(position['leverage'])
    
    unrealized_pnl = float(position['unrealizedProfit'])
    margin = abs(quantity * entry_price) / leverage
    roe = (unrealized_pnl / margin * 100) if margin > 0 else 0
    
    return {
        'symbol': position['symbol'],
        'exchange': 'PI42',
        'side': side,
        'quantity': abs(quantity),
        'entry_price': entry_price,
        'mark_price': mark_price,
        'liquidation_price': float(position.get('liquidationPrice', 0)),
        'unrealized_pnl': round(unrealized_pnl, 2),
        'realized_pnl': float(position.get('realizedProfit', 0)),
        'margin': round(margin, 2),
        'leverage': leverage,
        'margin_mode': position.get('marginType', 'ISOLATED'),
        'margin_asset': position.get('marginAsset', 'USDT'),
        'roe': round(roe, 2),
        'funding_fee': float(position.get('accumulatedFunding', 0))
    }
```

#### Step 2.3: Add Liquidation Price Calculator

**File:** `broker/pi42/mapping/transform_data.py` (add to existing)

```python
def calculate_liquidation_price(
    entry_price: float,
    leverage: int,
    side: str,
    maintenance_margin_rate: float = 0.01
) -> float:
    """
    Calculate liquidation price for position.
    
    Args:
        entry_price: Position entry price
        leverage: Leverage multiplier
        side: LONG or SHORT
        maintenance_margin_rate: Maintenance margin rate (default 1%)
        
    Returns:
        Liquidation price
    """
    if side == 'LONG':
        # For LONG: liquidation when price drops
        liquidation_price = entry_price * (1 - 1/leverage + maintenance_margin_rate)
    else:  # SHORT
        # For SHORT: liquidation when price rises
        liquidation_price = entry_price * (1 + 1/leverage - maintenance_margin_rate)
    
    return liquidation_price


def calculate_required_margin(
    entry_price: float,
    quantity: float,
    leverage: int
) -> float:
    """
    Calculate required margin for position.
    
    Args:
        entry_price: Entry price
        quantity: Position quantity
        leverage: Leverage multiplier
        
    Returns:
        Required margin amount
    """
    notional_value = entry_price * quantity
    margin = notional_value / leverage
    return margin
```

#### Step 2.4: Test Position Management

**File:** `test/test_pi42_positions.py`

```python
"""Test Pi42 position management."""

import os
from broker.pi42.api.position_api import get_positions, close_position, calculate_position_pnl
from broker.pi42.api.data import BrokerData
from utils.encryption import encrypt_token


def test_get_positions():
    """Test getting positions."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    result, status = get_positions(auth_token)
    
    print("Positions:")
    print(f"  Status: {status}")
    print(f"  Count: {len(result.get('data', []))}")
    
    if result.get('data'):
        for pos in result['data']:
            print(f"\n  {pos['symbol']}:")
            print(f"    Side: {pos['side']}")
            print(f"    Quantity: {pos['quantity']}")
            print(f"    Entry: {pos['entry_price']}")
            print(f"    Mark: {pos['mark_price']}")
            print(f"    Liquidation: {pos['liquidation_price']}")
            print(f"    PnL: {pos['unrealized_pnl']}")
            print(f"    ROE: {pos['roe']}%")
            print(f"    Leverage: {pos['leverage']}x")
    
    assert status == 200


def test_pnl_calculation():
    """Test PnL calculation."""
    position = {
        'entry_price': 50000,
        'quantity': 0.1,
        'leverage': 10,
        'side': 'LONG'
    }
    
    mark_price = 51000
    
    pnl_data = calculate_position_pnl(position, mark_price)
    
    print("\nPnL Calculation:")
    print(f"  Entry: {position['entry_price']}")
    print(f"  Mark: {mark_price}")
    print(f"  Unrealized PnL: {pnl_data['unrealized_pnl']}")
    print(f"  Margin: {pnl_data['margin']}")
    print(f"  ROE: {pnl_data['roe']}%")
    print(f"  Liquidation: {pnl_data['liquidation_price']}")
    
    # Verify calculations
    expected_pnl = (51000 - 50000) * 0.1  # 100
    assert abs(pnl_data['unrealized_pnl'] - expected_pnl) < 0.01


if __name__ == '__main__':
    test_get_positions()
    test_pnl_calculation()
    print("\n✓ Position management tests passed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_positions.py -v -s
```

---

### Day 5: Smart Order Implementation

#### Step 3.1: Create Smart Order Logic

**File:** `broker/pi42/api/smart_order.py` (create new)

```python
"""Smart order implementation for Pi42."""

from typing import Dict, Tuple
from broker.pi42.api.position_api import get_positions
from broker.pi42.api.order_api import place_order_api


class SmartOrderHandler:
    """Handle smart order logic for crypto futures."""
    
    def __init__(self, auth_token: str):
        """Initialize with auth token."""
        self.auth_token = auth_token
        self._position_cache = {}
    
    def refresh_positions(self) -> None:
        """Refresh position cache."""
        result, status = get_positions(self.auth_token)
        
        if status == 200 and result.get('data'):
            self._position_cache = {
                pos['symbol']: pos
                for pos in result['data']
            }
    
    def get_position(self, symbol: str) -> Dict:
        """
        Get position for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position data or empty dict
        """
        return self._position_cache.get(symbol, {})
    
    def place_smart_order(self, order_data: Dict) -> Tuple[Dict, int]:
        """
        Place smart order with position awareness.
        
        Args:
            order_data: Order data
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        symbol = order_data['symbol']
        action = order_data['action']
        quantity = float(order_data['quantity'])
        
        # Refresh positions
        self.refresh_positions()
        
        # Get current position
        position = self.get_position(symbol)
        
        if not position:
            # No position - place normal order
            return place_order_api(order_data, self.auth_token)
        
        # Check if order closes or reverses position
        position_qty = position['quantity']
        position_side = position['side']
        
        is_closing = (
            (position_side == 'LONG' and action == 'SELL') or
            (position_side == 'SHORT' and action == 'BUY')
        )
        
        if is_closing:
            if quantity == position_qty:
                # Exact close
                return place_order_api(order_data, self.auth_token)
            elif quantity < position_qty:
                # Partial close
                return place_order_api(order_data, self.auth_token)
            else:
                # Reverse position
                # First close existing, then open opposite
                close_order = order_data.copy()
                close_order['quantity'] = str(position_qty)
                
                # Close existing position
                result, status = place_order_api(close_order, self.auth_token)
                
                if status != 200:
                    return result, status
                
                # Open opposite position
                remaining_qty = quantity - position_qty
                reverse_order = order_data.copy()
                reverse_order['quantity'] = str(remaining_qty)
                
                return place_order_api(reverse_order, self.auth_token)
        else:
            # Adding to position
            return place_order_api(order_data, self.auth_token)


def create_smart_order_handler(auth_token: str) -> SmartOrderHandler:
    """
    Create smart order handler instance.
    
    Args:
        auth_token: Encrypted auth token
        
    Returns:
        SmartOrderHandler instance
    """
    return SmartOrderHandler(auth_token)
```

#### Step 3.2: Test Smart Orders

**File:** `test/test_pi42_smart_orders.py`

```python
"""Test Pi42 smart orders."""

import os
from broker.pi42.api.smart_order import create_smart_order_handler
from utils.encryption import encrypt_token


def test_smart_order_no_position():
    """Test smart order with no existing position."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    handler = create_smart_order_handler(auth_token)
    
    order_data = {
        'symbol': 'ETHUSDT',
        'action': 'BUY',
        'quantity': '0.01',
        'pricetype': 'MARKET',
        'leverage': 1,
        'margin_mode': 'ISOLATED',
        'margin_asset': 'USDT'
    }
    
    result, status = handler.place_smart_order(order_data)
    
    print("Smart Order (No Position):")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    assert status == 200


if __name__ == '__main__':
    test_smart_order_no_position()
    print("\n✓ Smart order tests passed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_smart_orders.py -v -s
```

---

## Week 3 Completion Checklist

- [ ] STOP_MARKET orders implemented
- [ ] STOP_LIMIT orders implemented
- [ ] Order modification working
- [ ] Position retrieval implemented
- [ ] Position close functionality working
- [ ] PnL calculations accurate
- [ ] Liquidation price calculator working
- [ ] Smart order logic implemented
- [ ] All tests passing

**Verification:**
```bash
uv run python -c "
from broker.pi42.api.order_api import place_stop_order
from broker.pi42.api.position_api import get_positions, calculate_position_pnl
from broker.pi42.mapping.transform_data import calculate_liquidation_price

print('✓ STOP order functions available')
print('✓ Position management functions available')
print('✓ PnL calculation functions available')

# Test liquidation calculation
liq_price = calculate_liquidation_price(50000, 10, 'LONG')
print(f'\\nLiquidation price (50k entry, 10x LONG): {liq_price}')

print('\\n✓ Week 3 advanced orders complete')
"
```

---

## Next: Week 4 - Leverage & Margin Management

Continue to `PHASE-2-WEEK-4.md` for:
- Leverage management API
- Margin add/reduce operations
- Data transformation completion
- Integration testing
