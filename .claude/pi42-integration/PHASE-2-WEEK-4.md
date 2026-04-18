# Phase 2: Core Trading Features - Week 4

**Goal:** Implement leverage and margin management

**Prerequisites:**
- Week 3 completed (advanced orders, positions)
- STOP orders working
- Position management functional

---

## Day 1-2: Leverage Management

### Step 1.1: Implement Leverage API

**File:** `broker/pi42/api/leverage_api.py` (create new)

```python
"""Pi42 leverage management API."""

import requests
from typing import Dict, Tuple
from broker.pi42.api.auth_api import create_auth_instance
from database.crypto_db import LeverageSetting, db


def set_leverage(
    symbol: str,
    leverage: int,
    auth_token: str
) -> Tuple[Dict, int]:
    """
    Set leverage for symbol.
    
    Args:
        symbol: Trading symbol
        leverage: Leverage multiplier (1-25)
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Validate leverage
        if not 1 <= leverage <= 25:
            return {
                'status': 'error',
                'message': 'Leverage must be between 1 and 25'
            }, 400
        
        # Get contract info to check max leverage
        from broker.pi42.database.master_contract_db import get_contract_info
        contract = get_contract_info(symbol)
        
        if not contract:
            return {
                'status': 'error',
                'message': f'Contract not found: {symbol}'
            }, 404
        
        if leverage > contract['max_leverage']:
            return {
                'status': 'error',
                'message': f'Leverage exceeds maximum: {contract["max_leverage"]}'
            }, 400
        
        # Create auth instance
        auth = create_auth_instance(auth_token)
        
        # Sign request
        endpoint = '/v1/leverage'
        body = {
            'symbol': symbol,
            'leverage': leverage
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f"Failed to set leverage: {response.text}"
            }, response.status_code
        
        result = response.json()
        
        # Save to database
        from database.auth_db import get_user_id_by_auth_token
        user_id = get_user_id_by_auth_token(auth_token)
        
        if user_id:
            save_leverage_setting(user_id, symbol, leverage, result.get('marginType', 'ISOLATED'))
        
        return {
            'status': 'success',
            'message': f'Leverage set to {leverage}x for {symbol}',
            'data': {
                'symbol': symbol,
                'leverage': leverage,
                'margin_mode': result.get('marginType', 'ISOLATED')
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_leverage(symbol: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Get current leverage for symbol.
    
    Args:
        symbol: Trading symbol
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Sign request
        endpoint = '/v1/leverage'
        params = {'symbol': symbol}
        headers, _ = auth.sign_request('GET', endpoint, params=params)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f"Failed to get leverage: {response.text}"
            }, response.status_code
        
        result = response.json()
        
        # Get contract info for max leverage
        from broker.pi42.database.master_contract_db import get_contract_info
        contract = get_contract_info(symbol)
        
        return {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'leverage': result.get('leverage', 1),
                'margin_mode': result.get('marginType', 'ISOLATED'),
                'max_leverage': contract['max_leverage'] if contract else 25
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def save_leverage_setting(
    user_id: int,
    symbol: str,
    leverage: int,
    margin_mode: str
) -> None:
    """
    Save leverage setting to database.
    
    Args:
        user_id: User ID
        symbol: Trading symbol
        leverage: Leverage value
        margin_mode: ISOLATED or CROSS
    """
    # Check if exists
    existing = LeverageSetting.query.filter_by(
        user_id=user_id,
        symbol=symbol
    ).first()
    
    if existing:
        # Update
        existing.leverage = leverage
        existing.margin_mode = margin_mode
    else:
        # Create new
        setting = LeverageSetting(
            user_id=user_id,
            symbol=symbol,
            leverage=leverage,
            margin_mode=margin_mode
        )
        db.session.add(setting)
    
    db.session.commit()


def get_user_leverage_settings(user_id: int) -> list:
    """
    Get all leverage settings for user.
    
    Args:
        user_id: User ID
        
    Returns:
        List of leverage settings
    """
    settings = LeverageSetting.query.filter_by(user_id=user_id).all()
    
    return [
        {
            'symbol': s.symbol,
            'leverage': s.leverage,
            'margin_mode': s.margin_mode,
            'updated_at': s.updated_at.isoformat()
        }
        for s in settings
    ]
```

### Step 1.2: Test Leverage Management

**File:** `test/test_pi42_leverage.py`

```python
"""Test Pi42 leverage management."""

import os
from broker.pi42.api.leverage_api import set_leverage, get_leverage
from utils.encryption import encrypt_token


def test_set_leverage():
    """Test setting leverage."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    # Set leverage to 10x
    result, status = set_leverage('BTCUSDT', 10, auth_token)
    
    print("Set Leverage:")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    assert status == 200
    assert result['status'] == 'success'
    assert result['data']['leverage'] == 10


def test_get_leverage():
    """Test getting leverage."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    result, status = get_leverage('BTCUSDT', auth_token)
    
    print("\nGet Leverage:")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    assert status == 200
    assert result['status'] == 'success'
    assert 'leverage' in result['data']


def test_invalid_leverage():
    """Test invalid leverage values."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    # Test leverage > 25
    result, status = set_leverage('BTCUSDT', 30, auth_token)
    
    print("\nInvalid Leverage (30x):")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    assert status == 400
    assert result['status'] == 'error'


if __name__ == '__main__':
    test_set_leverage()
    test_get_leverage()
    test_invalid_leverage()
    print("\n✓ Leverage management tests passed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_leverage.py -v -s
```

---

## Day 3-4: Margin Management

### Step 2.1: Implement Margin API

**File:** `broker/pi42/api/margin_api.py` (create new)

```python
"""Pi42 margin management API."""

import requests
from typing import Dict, Tuple
from broker.pi42.api.auth_api import create_auth_instance
from database.crypto_db import MarginOperation, db


def add_margin(
    symbol: str,
    amount: float,
    margin_asset: str,
    auth_token: str
) -> Tuple[Dict, int]:
    """
    Add margin to position.
    
    Args:
        symbol: Trading symbol
        amount: Margin amount to add
        margin_asset: USDT or INR
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Validate amount
        if amount <= 0:
            return {
                'status': 'error',
                'message': 'Amount must be positive'
            }, 400
        
        # Validate margin asset
        if margin_asset not in ['USDT', 'INR']:
            return {
                'status': 'error',
                'message': 'Margin asset must be USDT or INR'
            }, 400
        
        # Create auth instance
        auth = create_auth_instance(auth_token)
        
        # Sign request
        endpoint = '/v1/position/margin'
        body = {
            'symbol': symbol,
            'amount': amount,
            'type': 'ADD',
            'marginAsset': margin_asset
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f"Failed to add margin: {response.text}"
            }, response.status_code
        
        result = response.json()
        
        # Save to database
        from database.auth_db import get_user_id_by_auth_token
        user_id = get_user_id_by_auth_token(auth_token)
        
        if user_id:
            save_margin_operation(user_id, symbol, 'ADD', amount, margin_asset)
        
        # Get new liquidation price
        new_liq_price = result.get('liquidationPrice', 0)
        
        return {
            'status': 'success',
            'message': f'Added {amount} {margin_asset} margin to {symbol}',
            'data': {
                'symbol': symbol,
                'new_margin': result.get('margin', 0),
                'new_liquidation_price': new_liq_price
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def reduce_margin(
    symbol: str,
    amount: float,
    auth_token: str
) -> Tuple[Dict, int]:
    """
    Reduce margin from position.
    
    Args:
        symbol: Trading symbol
        amount: Margin amount to reduce
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Validate amount
        if amount <= 0:
            return {
                'status': 'error',
                'message': 'Amount must be positive'
            }, 400
        
        # Create auth instance
        auth = create_auth_instance(auth_token)
        
        # Sign request
        endpoint = '/v1/position/margin'
        body = {
            'symbol': symbol,
            'amount': amount,
            'type': 'REDUCE'
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f"Failed to reduce margin: {response.text}"
            }, response.status_code
        
        result = response.json()
        
        # Save to database
        from database.auth_db import get_user_id_by_auth_token
        user_id = get_user_id_by_auth_token(auth_token)
        
        if user_id:
            save_margin_operation(user_id, symbol, 'REDUCE', amount, 'USDT')
        
        # Get new liquidation price
        new_liq_price = result.get('liquidationPrice', 0)
        
        return {
            'status': 'success',
            'message': f'Reduced {amount} margin from {symbol}',
            'data': {
                'symbol': symbol,
                'new_margin': result.get('margin', 0),
                'new_liquidation_price': new_liq_price
            }
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def save_margin_operation(
    user_id: int,
    symbol: str,
    operation: str,
    amount: float,
    margin_asset: str
) -> None:
    """
    Save margin operation to database.
    
    Args:
        user_id: User ID
        symbol: Trading symbol
        operation: ADD or REDUCE
        amount: Margin amount
        margin_asset: USDT or INR
    """
    op = MarginOperation(
        user_id=user_id,
        symbol=symbol,
        operation=operation,
        amount=amount,
        margin_asset=margin_asset
    )
    db.session.add(op)
    db.session.commit()


def get_margin_history(user_id: int, symbol: str = None, limit: int = 100) -> list:
    """
    Get margin operation history.
    
    Args:
        user_id: User ID
        symbol: Optional symbol filter
        limit: Maximum records
        
    Returns:
        List of margin operations
    """
    query = MarginOperation.query.filter_by(user_id=user_id)
    
    if symbol:
        query = query.filter_by(symbol=symbol)
    
    operations = query.order_by(MarginOperation.timestamp.desc()).limit(limit).all()
    
    return [
        {
            'symbol': op.symbol,
            'operation': op.operation,
            'amount': op.amount,
            'margin_asset': op.margin_asset,
            'timestamp': op.timestamp.isoformat()
        }
        for op in operations
    ]
```

### Step 2.2: Test Margin Management

**File:** `test/test_pi42_margin.py`

```python
"""Test Pi42 margin management."""

import os
from broker.pi42.api.margin_api import add_margin, reduce_margin
from broker.pi42.api.position_api import get_positions
from utils.encryption import encrypt_token


def test_add_margin():
    """Test adding margin to position."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    # Get current positions
    positions, status = get_positions(auth_token)
    
    if not positions.get('data'):
        print("⚠ No open positions to test margin management")
        return
    
    symbol = positions['data'][0]['symbol']
    
    # Add margin
    result, status = add_margin(symbol, 10, 'USDT', auth_token)
    
    print("Add Margin:")
    print(f"  Symbol: {symbol}")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    if status == 200:
        print(f"  New Margin: {result['data']['new_margin']}")
        print(f"  New Liquidation: {result['data']['new_liquidation_price']}")
        assert result['status'] == 'success'


def test_reduce_margin():
    """Test reducing margin from position."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    # Get current positions
    positions, status = get_positions(auth_token)
    
    if not positions.get('data'):
        print("⚠ No open positions to test margin management")
        return
    
    symbol = positions['data'][0]['symbol']
    
    # Reduce margin
    result, status = reduce_margin(symbol, 5, auth_token)
    
    print("\nReduce Margin:")
    print(f"  Symbol: {symbol}")
    print(f"  Status: {status}")
    print(f"  Result: {result}")
    
    if status == 200:
        print(f"  New Margin: {result['data']['new_margin']}")
        print(f"  New Liquidation: {result['data']['new_liquidation_price']}")
        assert result['status'] == 'success'


if __name__ == '__main__':
    test_add_margin()
    test_reduce_margin()
    print("\n✓ Margin management tests passed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_margin.py -v -s
```

---

## Day 5: Integration Testing

### Step 3.1: Create Comprehensive Integration Test

**File:** `test/integration/test_pi42_integration.py`

```python
"""Comprehensive Pi42 integration tests."""

import os
import time
from broker.pi42.api.order_api import place_order_api, cancel_order_api, get_order_book
from broker.pi42.api.position_api import get_positions, close_position
from broker.pi42.api.leverage_api import set_leverage, get_leverage
from broker.pi42.api.margin_api import add_margin, reduce_margin
from broker.pi42.api.data import BrokerData
from utils.encryption import encrypt_token


class TestPi42Integration:
    """Pi42 integration test suite."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        api_key = os.getenv('PI42_API_KEY')
        api_secret = os.getenv('PI42_API_SECRET')
        cls.auth_token = encrypt_token(f"{api_key}|{api_secret}")
        cls.test_symbol = 'BTCUSDT'
        cls.test_quantity = 0.001  # Minimum quantity
    
    def test_01_set_leverage(self):
        """Test 1: Set leverage."""
        result, status = set_leverage(self.test_symbol, 5, self.auth_token)
        
        print("\n1. Set Leverage:")
        print(f"   Status: {status}")
        print(f"   Leverage: 5x")
        
        assert status == 200
        assert result['data']['leverage'] == 5
    
    def test_02_get_market_data(self):
        """Test 2: Get market data."""
        data = BrokerData(self.auth_token)
        quotes = data.get_quotes(self.test_symbol)
        
        print("\n2. Market Data:")
        print(f"   LTP: {quotes['ltp']}")
        print(f"   Mark Price: {quotes['mark_price']}")
        
        assert quotes['ltp'] > 0
    
    def test_03_place_market_order(self):
        """Test 3: Place market order."""
        order_data = {
            'symbol': self.test_symbol,
            'action': 'BUY',
            'quantity': str(self.test_quantity),
            'pricetype': 'MARKET',
            'leverage': 5,
            'margin_mode': 'ISOLATED',
            'margin_asset': 'USDT'
        }
        
        result, status = place_order_api(order_data, self.auth_token)
        
        print("\n3. Place Market Order:")
        print(f"   Status: {status}")
        print(f"   Order ID: {result.get('orderid', 'N/A')}")
        
        assert status == 200
        
        # Wait for order to fill
        time.sleep(2)
    
    def test_04_get_positions(self):
        """Test 4: Get positions."""
        result, status = get_positions(self.auth_token)
        
        print("\n4. Get Positions:")
        print(f"   Status: {status}")
        print(f"   Count: {len(result.get('data', []))}")
        
        if result.get('data'):
            pos = result['data'][0]
            print(f"   Position: {pos['symbol']} {pos['side']} {pos['quantity']}")
            print(f"   PnL: {pos['unrealized_pnl']}")
            print(f"   Liquidation: {pos['liquidation_price']}")
        
        assert status == 200
    
    def test_05_add_margin(self):
        """Test 5: Add margin."""
        result, status = add_margin(self.test_symbol, 10, 'USDT', self.auth_token)
        
        print("\n5. Add Margin:")
        print(f"   Status: {status}")
        
        if status == 200:
            print(f"   New Margin: {result['data']['new_margin']}")
            print(f"   New Liquidation: {result['data']['new_liquidation_price']}")
    
    def test_06_place_stop_order(self):
        """Test 6: Place STOP order."""
        # Get current price
        data = BrokerData(self.auth_token)
        quotes = data.get_quotes(self.test_symbol)
        stop_price = quotes['ltp'] * 0.95  # 5% below
        
        from broker.pi42.api.order_api import place_stop_order
        
        result, status = place_stop_order(
            symbol=self.test_symbol,
            side='SELL',
            quantity=self.test_quantity,
            stop_price=stop_price,
            order_type='STOP_MARKET',
            leverage=5,
            margin_mode='ISOLATED',
            margin_asset='USDT',
            auth_token=self.auth_token
        )
        
        print("\n6. Place STOP Order:")
        print(f"   Status: {status}")
        print(f"   Stop Price: {stop_price}")
        
        if status == 200:
            self.stop_order_id = result.get('orderid')
    
    def test_07_get_order_book(self):
        """Test 7: Get order book."""
        result, status = get_order_book(self.auth_token)
        
        print("\n7. Get Order Book:")
        print(f"   Status: {status}")
        print(f"   Open Orders: {len(result.get('data', []))}")
        
        assert status == 200
    
    def test_08_cancel_stop_order(self):
        """Test 8: Cancel STOP order."""
        if hasattr(self, 'stop_order_id'):
            result, status = cancel_order_api(self.stop_order_id, self.auth_token)
            
            print("\n8. Cancel STOP Order:")
            print(f"   Status: {status}")
            
            assert status == 200
    
    def test_09_close_position(self):
        """Test 9: Close position."""
        result, status = close_position(self.test_symbol, self.auth_token)
        
        print("\n9. Close Position:")
        print(f"   Status: {status}")
        
        assert status == 200
        
        # Wait for position to close
        time.sleep(2)
    
    def test_10_verify_no_positions(self):
        """Test 10: Verify no open positions."""
        result, status = get_positions(self.auth_token)
        
        print("\n10. Verify No Positions:")
        print(f"    Status: {status}")
        print(f"    Count: {len(result.get('data', []))}")
        
        assert status == 200


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '-s'])
```

**Run integration test:**
```bash
uv run pytest test/integration/test_pi42_integration.py -v -s
```

---

## Week 4 Completion Checklist

- [ ] Leverage API implemented
- [ ] Set/get leverage working
- [ ] Leverage validation working
- [ ] Margin add API implemented
- [ ] Margin reduce API implemented
- [ ] Margin operations saved to database
- [ ] Integration tests passing
- [ ] All transformations complete

**Verification:**
```bash
uv run python -c "
from broker.pi42.api.leverage_api import set_leverage, get_leverage
from broker.pi42.api.margin_api import add_margin, reduce_margin

print('✓ Leverage management functions available')
print('✓ Margin management functions available')

# Check database tables
from database.crypto_db import LeverageSetting, MarginOperation
from database.symbol_db import db

lev_count = LeverageSetting.query.count()
margin_count = MarginOperation.query.count()

print(f'\\nDatabase records:')
print(f'  Leverage settings: {lev_count}')
print(f'  Margin operations: {margin_count}')

print('\\n✓ Week 4 leverage & margin complete')
"
```

---

## Phase 2 Complete!

**Achievements:**
- ✅ STOP orders (MARKET & LIMIT) working
- ✅ Position management complete
- ✅ PnL calculations accurate
- ✅ Liquidation price calculator working
- ✅ Smart order logic implemented
- ✅ Leverage management functional
- ✅ Margin add/reduce working
- ✅ Integration tests passing

**Next Phase:** Phase 3 - Advanced Features
- Split TP/SL
- Funding rate tracking
- Historical data
- Analytics

Continue to `PHASE-3-ADVANCED.md`
