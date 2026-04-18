# Phase 3: Advanced Features - Week 5

**Goal:** Implement crypto-specific advanced features

**Prerequisites:**
- Phase 2 completed (core trading features)
- Leverage and margin management working
- All basic order types functional

---

## Day 1-2: Split TP/SL Implementation

### Step 1.1: Create Split TP/SL API

**File:** `broker/pi42/api/split_tpsl_api.py` (create new)

```python
"""Pi42 split take-profit and stop-loss API."""

import requests
from typing import Dict, List, Tuple
from broker.pi42.api.auth_api import create_auth_instance
from broker.pi42.api.order_api import place_stop_order


def place_split_takeprofit(
    symbol: str,
    tp_levels: List[Dict],
    auth_token: str
) -> Tuple[Dict, int]:
    """
    Place multiple take-profit orders at different levels.
    
    Args:
        symbol: Trading symbol
        tp_levels: List of TP levels [{'price': float, 'quantity': float}, ...]
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Validate TP levels
        if not tp_levels:
            return {
                'status': 'error',
                'message': 'At least one TP level required'
            }, 400
        
        # Validate total quantity doesn't exceed position
        from broker.pi42.api.position_api import get_positions
        positions_result, status = get_positions(auth_token)
        
        if status != 200:
            return positions_result, status
        
        # Find position
        position = None
        for pos in positions_result.get('data', []):
            if pos['symbol'] == symbol:
                position = pos
                break
        
        if not position:
            return {
                'status': 'error',
                'message': f'No open position for {symbol}'
            }, 404
        
        # Validate quantities
        total_tp_qty = sum(level['quantity'] for level in tp_levels)
        position_qty = position['quantity']
        
        if total_tp_qty > position_qty:
            return {
                'status': 'error',
                'message': f'Total TP quantity ({total_tp_qty}) exceeds position ({position_qty})'
            }, 400
        
        # Place TP orders
        tp_order_ids = []
        side = 'SELL' if position['side'] == 'LONG' else 'BUY'
        
        for i, level in enumerate(tp_levels):
            result, status = place_stop_order(
                symbol=symbol,
                side=side,
                quantity=level['quantity'],
                stop_price=level['price'],
                order_type='STOP_LIMIT',
                limit_price=level['price'],  # Same as stop for TP
                leverage=position.get('leverage', 1),
                margin_mode=position.get('margin_mode', 'ISOLATED'),
                margin_asset=position.get('margin_asset', 'USDT'),
                auth_token=auth_token
            )
            
            if status == 200:
                tp_order_ids.append(result['orderid'])
            else:
                # Cancel previously placed orders on failure
                from broker.pi42.api.order_api import cancel_order_api
                for order_id in tp_order_ids:
                    cancel_order_api(order_id, auth_token)
                
                return {
                    'status': 'error',
                    'message': f'Failed to place TP level {i+1}: {result.get("message")}'
                }, status
        
        return {
            'status': 'success',
            'message': f'Placed {len(tp_order_ids)} take-profit orders',
            'data': {
                'symbol': symbol,
                'tp_orders': tp_order_ids,
                'levels': tp_levels
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def place_split_stoploss(
    symbol: str,
    sl_levels: List[Dict],
    auth_token: str
) -> Tuple[Dict, int]:
    """
    Place multiple stop-loss orders at different levels.
    
    Args:
        symbol: Trading symbol
        sl_levels: List of SL levels [{'price': float, 'quantity': float}, ...]
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Validate SL levels
        if not sl_levels:
            return {
                'status': 'error',
                'message': 'At least one SL level required'
            }, 400
        
        # Get position
        from broker.pi42.api.position_api import get_positions
        positions_result, status = get_positions(auth_token)
        
        if status != 200:
            return positions_result, status
        
        # Find position
        position = None
        for pos in positions_result.get('data', []):
            if pos['symbol'] == symbol:
                position = pos
                break
        
        if not position:
            return {
                'status': 'error',
                'message': f'No open position for {symbol}'
            }, 404
        
        # Validate quantities
        total_sl_qty = sum(level['quantity'] for level in sl_levels)
        position_qty = position['quantity']
        
        if total_sl_qty > position_qty:
            return {
                'status': 'error',
                'message': f'Total SL quantity ({total_sl_qty}) exceeds position ({position_qty})'
            }, 400
        
        # Place SL orders
        sl_order_ids = []
        side = 'SELL' if position['side'] == 'LONG' else 'BUY'
        
        for i, level in enumerate(sl_levels):
            result, status = place_stop_order(
                symbol=symbol,
                side=side,
                quantity=level['quantity'],
                stop_price=level['price'],
                order_type='STOP_MARKET',
                leverage=position.get('leverage', 1),
                margin_mode=position.get('margin_mode', 'ISOLATED'),
                margin_asset=position.get('margin_asset', 'USDT'),
                auth_token=auth_token
            )
            
            if status == 200:
                sl_order_ids.append(result['orderid'])
            else:
                # Cancel previously placed orders on failure
                from broker.pi42.api.order_api import cancel_order_api
                for order_id in sl_order_ids:
                    cancel_order_api(order_id, auth_token)
                
                return {
                    'status': 'error',
                    'message': f'Failed to place SL level {i+1}: {result.get("message")}'
                }, status
        
        return {
            'status': 'success',
            'message': f'Placed {len(sl_order_ids)} stop-loss orders',
            'data': {
                'symbol': symbol,
                'sl_orders': sl_order_ids,
                'levels': sl_levels
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def place_split_tpsl(
    symbol: str,
    tp_levels: List[Dict],
    sl_levels: List[Dict],
    auth_token: str
) -> Tuple[Dict, int]:
    """
    Place both split TP and SL orders.
    
    Args:
        symbol: Trading symbol
        tp_levels: List of TP levels
        sl_levels: List of SL levels
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Place TP orders
        tp_result, tp_status = place_split_takeprofit(symbol, tp_levels, auth_token)
        
        if tp_status != 200:
            return tp_result, tp_status
        
        # Place SL orders
        sl_result, sl_status = place_split_stoploss(symbol, sl_levels, auth_token)
        
        if sl_status != 200:
            # Cancel TP orders on SL failure
            from broker.pi42.api.order_api import cancel_order_api
            for order_id in tp_result['data']['tp_orders']:
                cancel_order_api(order_id, auth_token)
            
            return sl_result, sl_status
        
        return {
            'status': 'success',
            'message': 'Split TP/SL orders placed successfully',
            'data': {
                'symbol': symbol,
                'tp_orders': tp_result['data']['tp_orders'],
                'sl_orders': sl_result['data']['sl_orders'],
                'tp_levels': tp_levels,
                'sl_levels': sl_levels
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500
```

### Step 1.2: Test Split TP/SL

**File:** `test/test_pi42_split_tpsl.py`

```python
"""Test Pi42 split TP/SL."""

import os
from broker.pi42.api.split_tpsl_api import place_split_tpsl
from broker.pi42.api.order_api import place_order_api
from broker.pi42.api.data import BrokerData
from utils.encryption import encrypt_token
import time


def test_split_tpsl():
    """Test split TP/SL orders."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    symbol = 'BTCUSDT'
    
    # First, open a position
    print("Opening position...")
    order_data = {
        'symbol': symbol,
        'action': 'BUY',
        'quantity': '0.003',  # 3x minimum for 3 TP levels
        'pricetype': 'MARKET',
        'leverage': 5,
        'margin_mode': 'ISOLATED',
        'margin_asset': 'USDT'
    }
    
    result, status = place_order_api(order_data, auth_token)
    print(f"Position opened: {status}")
    
    # Wait for order to fill
    time.sleep(3)
    
    # Get current price
    data = BrokerData(auth_token)
    quotes = data.get_quotes(symbol)
    current_price = quotes['ltp']
    
    # Define TP levels (2%, 4%, 6% profit)
    tp_levels = [
        {'price': current_price * 1.02, 'quantity': 0.001},
        {'price': current_price * 1.04, 'quantity': 0.001},
        {'price': current_price * 1.06, 'quantity': 0.001}
    ]
    
    # Define SL levels (2% loss)
    sl_levels = [
        {'price': current_price * 0.98, 'quantity': 0.003}
    ]
    
    # Place split TP/SL
    result, status = place_split_tpsl(symbol, tp_levels, sl_levels, auth_token)
    
    print("\nSplit TP/SL:")
    print(f"  Status: {status}")
    print(f"  TP Orders: {len(result.get('data', {}).get('tp_orders', []))}")
    print(f"  SL Orders: {len(result.get('data', {}).get('sl_orders', []))}")
    
    if status == 200:
        print(f"\n  TP Levels:")
        for i, level in enumerate(tp_levels):
            print(f"    {i+1}. Price: {level['price']:.2f}, Qty: {level['quantity']}")
        
        print(f"\n  SL Levels:")
        for i, level in enumerate(sl_levels):
            print(f"    {i+1}. Price: {level['price']:.2f}, Qty: {level['quantity']}")
    
    assert status == 200


if __name__ == '__main__':
    test_split_tpsl()
    print("\n✓ Split TP/SL test passed")
    print("Note: Cancel orders and close position manually")
```

**Run test:**
```bash
uv run pytest test/test_pi42_split_tpsl.py -v -s
```

---

## Day 3-4: Funding Rate System

### Step 2.1: Create Funding Rate API

**File:** `broker/pi42/api/funding_api.py` (create new)

```python
"""Pi42 funding rate API."""

import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from broker.pi42.api.auth_api import create_auth_instance
from database.crypto_db import FundingRate, db


def get_funding_rate(symbol: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Get current funding rate for symbol.
    
    Args:
        symbol: Trading symbol
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Sign request
        endpoint = '/v1/fundingRate'
        params = {'symbol': symbol}
        headers, _ = auth.sign_request('GET', endpoint, params=params)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f"Failed to get funding rate: {response.text}"
            }, response.status_code
        
        data = response.json()
        
        # Save to database
        save_funding_rate(
            symbol=symbol,
            funding_rate=float(data['fundingRate']),
            funding_time=datetime.fromtimestamp(data['fundingTime'] / 1000),
            mark_price=float(data.get('markPrice', 0)),
            index_price=float(data.get('indexPrice', 0))
        )
        
        return {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'funding_rate': float(data['fundingRate']),
                'next_funding_time': data['fundingTime'],
                'mark_price': float(data.get('markPrice', 0)),
                'index_price': float(data.get('indexPrice', 0))
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_funding_history(
    symbol: str,
    limit: int = 100,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> List[Dict]:
    """
    Get funding rate history from database.
    
    Args:
        symbol: Trading symbol
        limit: Maximum records
        start_time: Start timestamp (ms)
        end_time: End timestamp (ms)
        
    Returns:
        List of funding rate records
    """
    query = FundingRate.query.filter_by(symbol=symbol)
    
    if start_time:
        query = query.filter(FundingRate.funding_time >= datetime.fromtimestamp(start_time / 1000))
    
    if end_time:
        query = query.filter(FundingRate.funding_time <= datetime.fromtimestamp(end_time / 1000))
    
    records = query.order_by(FundingRate.funding_time.desc()).limit(limit).all()
    
    return [
        {
            'symbol': r.symbol,
            'funding_rate': r.funding_rate,
            'funding_time': int(r.funding_time.timestamp() * 1000),
            'mark_price': r.mark_price,
            'index_price': r.index_price
        }
        for r in records
    ]


def save_funding_rate(
    symbol: str,
    funding_rate: float,
    funding_time: datetime,
    mark_price: float,
    index_price: float
) -> None:
    """
    Save funding rate to database.
    
    Args:
        symbol: Trading symbol
        funding_rate: Funding rate value
        funding_time: Funding timestamp
        mark_price: Mark price
        index_price: Index price
    """
    # Check if already exists
    existing = FundingRate.query.filter_by(
        symbol=symbol,
        funding_time=funding_time
    ).first()
    
    if not existing:
        record = FundingRate(
            symbol=symbol,
            funding_rate=funding_rate,
            funding_time=funding_time,
            mark_price=mark_price,
            index_price=index_price
        )
        db.session.add(record)
        db.session.commit()


def calculate_funding_fee(
    position_value: float,
    funding_rate: float
) -> float:
    """
    Calculate funding fee for position.
    
    Args:
        position_value: Position notional value
        funding_rate: Current funding rate
        
    Returns:
        Funding fee amount (positive = pay, negative = receive)
    """
    return position_value * funding_rate
```

### Step 2.2: Test Funding Rate

**File:** `test/test_pi42_funding.py`

```python
"""Test Pi42 funding rate."""

import os
from broker.pi42.api.funding_api import get_funding_rate, get_funding_history, calculate_funding_fee
from utils.encryption import encrypt_token


def test_get_funding_rate():
    """Test getting funding rate."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    result, status = get_funding_rate('BTCUSDT', auth_token)
    
    print("Funding Rate:")
    print(f"  Status: {status}")
    
    if status == 200:
        data = result['data']
        print(f"  Symbol: {data['symbol']}")
        print(f"  Rate: {data['funding_rate']:.6f}")
        print(f"  Mark Price: {data['mark_price']}")
        print(f"  Index Price: {data['index_price']}")
        
        # Calculate fee for example position
        position_value = 5000  # $5000 position
        fee = calculate_funding_fee(position_value, data['funding_rate'])
        print(f"\n  Example: $5000 position")
        print(f"  Funding Fee: ${fee:.2f}")
    
    assert status == 200


def test_funding_history():
    """Test funding rate history."""
    history = get_funding_history('BTCUSDT', limit=10)
    
    print("\nFunding History:")
    print(f"  Records: {len(history)}")
    
    if history:
        print(f"\n  Latest 3:")
        for i, record in enumerate(history[:3]):
            print(f"    {i+1}. Rate: {record['funding_rate']:.6f}, Price: {record['mark_price']}")


if __name__ == '__main__':
    test_get_funding_rate()
    test_funding_history()
    print("\n✓ Funding rate tests passed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_funding.py -v -s
```

---

## Day 5: Liquidation System

### Step 3.1: Create Liquidation Calculator

**File:** `broker/pi42/api/liquidation_api.py` (create new)

```python
"""Pi42 liquidation calculator API."""

from typing import Dict, Tuple
from broker.pi42.mapping.transform_data import calculate_liquidation_price, calculate_required_margin
from broker.pi42.database.master_contract_db import get_contract_info


def calculate_liquidation_details(
    symbol: str,
    entry_price: float,
    quantity: float,
    leverage: int,
    side: str
) -> Tuple[Dict, int]:
    """
    Calculate liquidation details for position.
    
    Args:
        symbol: Trading symbol
        entry_price: Entry price
        quantity: Position quantity
        leverage: Leverage multiplier
        side: LONG or SHORT
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Get contract info
        contract = get_contract_info(symbol)
        
        if not contract:
            return {
                'status': 'error',
                'message': f'Contract not found: {symbol}'
            }, 404
        
        # Calculate liquidation price
        maintenance_margin_rate = contract.get('maintenance_margin_rate', 0.01)
        liq_price = calculate_liquidation_price(
            entry_price,
            leverage,
            side,
            maintenance_margin_rate
        )
        
        # Calculate required margin
        margin = calculate_required_margin(entry_price, quantity, leverage)
        
        # Calculate distance to liquidation
        if side == 'LONG':
            distance = ((entry_price - liq_price) / entry_price) * 100
        else:  # SHORT
            distance = ((liq_price - entry_price) / entry_price) * 100
        
        # Determine risk level
        if distance < 5:
            risk_level = 'critical'
        elif distance < 10:
            risk_level = 'high'
        elif distance < 20:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'entry_price': entry_price,
                'liquidation_price': round(liq_price, contract['price_precision']),
                'distance_percentage': round(distance, 2),
                'risk_level': risk_level,
                'margin': round(margin, 2),
                'leverage': leverage,
                'side': side,
                'maintenance_margin_rate': maintenance_margin_rate
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_risk_indicators(liquidation_distance: float) -> Dict:
    """
    Get risk indicators based on liquidation distance.
    
    Args:
        liquidation_distance: Distance to liquidation (%)
        
    Returns:
        Risk indicator dictionary
    """
    if liquidation_distance < 5:
        return {
            'level': 'critical',
            'color': 'red',
            'message': 'CRITICAL: Position at high risk of liquidation',
            'action': 'Add margin immediately or close position'
        }
    elif liquidation_distance < 10:
        return {
            'level': 'high',
            'color': 'orange',
            'message': 'HIGH RISK: Consider adding margin',
            'action': 'Monitor closely and add margin if needed'
        }
    elif liquidation_distance < 20:
        return {
            'level': 'medium',
            'color': 'yellow',
            'message': 'MEDIUM RISK: Position is safe but monitor',
            'action': 'Keep an eye on price movements'
        }
    else:
        return {
            'level': 'low',
            'color': 'green',
            'message': 'LOW RISK: Position is safe',
            'action': 'No action needed'
        }
```

### Step 3.2: Test Liquidation Calculator

**File:** `test/test_pi42_liquidation.py`

```python
"""Test Pi42 liquidation calculator."""

from broker.pi42.api.liquidation_api import calculate_liquidation_details, get_risk_indicators


def test_liquidation_long():
    """Test liquidation calculation for LONG position."""
    result, status = calculate_liquidation_details(
        symbol='BTCUSDT',
        entry_price=50000,
        quantity=0.1,
        leverage=10,
        side='LONG'
    )
    
    print("Liquidation (LONG):")
    print(f"  Status: {status}")
    
    if status == 200:
        data = result['data']
        print(f"  Entry: ${data['entry_price']}")
        print(f"  Liquidation: ${data['liquidation_price']}")
        print(f"  Distance: {data['distance_percentage']}%")
        print(f"  Risk Level: {data['risk_level']}")
        print(f"  Margin: ${data['margin']}")
    
    assert status == 200
    assert result['data']['liquidation_price'] < 50000  # Should be below entry


def test_liquidation_short():
    """Test liquidation calculation for SHORT position."""
    result, status = calculate_liquidation_details(
        symbol='BTCUSDT',
        entry_price=50000,
        quantity=0.1,
        leverage=10,
        side='SHORT'
    )
    
    print("\nLiquidation (SHORT):")
    print(f"  Status: {status}")
    
    if status == 200:
        data = result['data']
        print(f"  Entry: ${data['entry_price']}")
        print(f"  Liquidation: ${data['liquidation_price']}")
        print(f"  Distance: {data['distance_percentage']}%")
        print(f"  Risk Level: {data['risk_level']}")
    
    assert status == 200
    assert result['data']['liquidation_price'] > 50000  # Should be above entry


def test_risk_indicators():
    """Test risk indicators."""
    print("\nRisk Indicators:")
    
    for distance in [3, 8, 15, 25]:
        indicators = get_risk_indicators(distance)
        print(f"\n  {distance}% distance:")
        print(f"    Level: {indicators['level']}")
        print(f"    Message: {indicators['message']}")


if __name__ == '__main__':
    test_liquidation_long()
    test_liquidation_short()
    test_risk_indicators()
    print("\n✓ Liquidation calculator tests passed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_liquidation.py -v -s
```

---

## Week 5 Completion Checklist

- [ ] Split TP/SL API implemented
- [ ] Multiple TP levels working
- [ ] Multiple SL levels working
- [ ] Funding rate API implemented
- [ ] Funding history stored in database
- [ ] Funding fee calculator working
- [ ] Liquidation calculator implemented
- [ ] Risk indicators working
- [ ] All tests passing

**Verification:**
```bash
uv run python -c "
from broker.pi42.api.split_tpsl_api import place_split_tpsl
from broker.pi42.api.funding_api import get_funding_rate, calculate_funding_fee
from broker.pi42.api.liquidation_api import calculate_liquidation_details

print('✓ Split TP/SL functions available')
print('✓ Funding rate functions available')
print('✓ Liquidation calculator available')

# Test liquidation calculation
from broker.pi42.api.liquidation_api import calculate_liquidation_details
result, status = calculate_liquidation_details('BTCUSDT', 50000, 0.1, 10, 'LONG')
if status == 200:
    print(f'\\nLiquidation test:')
    print(f'  Entry: \$50,000')
    print(f'  Liquidation: \${result[\"data\"][\"liquidation_price\"]}')
    print(f'  Distance: {result[\"data\"][\"distance_percentage\"]}%')

print('\\n✓ Week 5 advanced features complete')
"
```

---

## Next: Week 6 - Historical Data & Analytics

Continue to `PHASE-3-WEEK-6.md` for:
- Historical klines API
- Portfolio analytics
- Contract info API
- Performance metrics
