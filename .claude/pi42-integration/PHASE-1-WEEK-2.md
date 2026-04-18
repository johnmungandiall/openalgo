# Phase 1: Foundation - Week 2

**Goal:** Implement basic integration with Pi42 API

**Prerequisites:**
- Week 1 completed (database schema, authentication)
- Pi42 test account active
- API credentials configured in .env

---

## Day 1-2: Master Contract Download

### Step 1.1: Create Master Contract Database Module

**File:** `broker/pi42/database/master_contract_db.py`

```python
"""Pi42 master contract database management."""

import requests
from typing import List, Dict, Optional
from sqlalchemy import text
from database.symbol_db import db, Symtoken


class Pi42MasterContract:
    """Pi42 master contract management."""
    
    def __init__(self, auth):
        """Initialize with Pi42Auth instance."""
        self.auth = auth
        self.base_url = auth.base_url
    
    def download_contracts(self) -> List[Dict]:
        """
        Download all contract specifications from Pi42.
        
        Returns:
            List of contract dictionaries
        """
        endpoint = '/v1/exchangeInfo'
        headers, _ = self.auth.sign_request('GET', endpoint)
        
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download contracts: {response.text}")
        
        data = response.json()
        return data.get('symbols', [])
    
    def process_contract(self, contract: Dict) -> Dict:
        """
        Process contract data into OpenAlgo format.
        
        Args:
            contract: Raw contract data from Pi42
            
        Returns:
            Processed contract dictionary
        """
        # Extract filters
        filters = {f['filterType']: f for f in contract.get('filters', [])}
        
        # Get precision from filters
        price_filter = filters.get('PRICE_FILTER', {})
        lot_size_filter = filters.get('LOT_SIZE', {})
        
        return {
            'symbol': contract['symbol'],
            'brsymbol': contract['symbol'],  # Pi42 uses same symbol
            'name': contract['symbol'],
            'exchange': 'PI42',
            'brexchange': 'PI42',
            'token': contract['symbol'],  # Use symbol as token
            'expiry': '',  # Perpetual contracts have no expiry
            'strike': 0.0,
            'lotsize': 1,
            'instrumenttype': 'FUTCOM',  # Futures Commodity
            'tick_size': float(price_filter.get('tickSize', 0.01)),
            
            # Crypto-specific fields
            'broker_type': 'CRYPTO_futures',
            'min_quantity': float(lot_size_filter.get('minQty', 0.001)),
            'max_quantity': float(lot_size_filter.get('maxQty', 1000)),
            'price_precision': self._get_precision(price_filter.get('tickSize', '0.01')),
            'quantity_precision': self._get_precision(lot_size_filter.get('stepSize', '0.001')),
            'margin_assets': ','.join(contract.get('marginAssets', ['USDT'])),
            'max_leverage': contract.get('maxLeverage', 25),
            'base_asset': contract.get('baseAsset', ''),
            'quote_asset': contract.get('quoteAsset', ''),
            'contract_type': 'PERPETUAL',
            'min_notional': float(filters.get('MIN_NOTIONAL', {}).get('minNotional', 10)),
            'maintenance_margin_rate': float(contract.get('maintMarginPercent', 0.01))
        }
    
    def _get_precision(self, value: str) -> int:
        """
        Get decimal precision from tick/step size.
        
        Args:
            value: Tick or step size as string
            
        Returns:
            Number of decimal places
        """
        if '.' not in str(value):
            return 0
        return len(str(value).split('.')[1].rstrip('0'))
    
    def save_to_database(self, contracts: List[Dict]) -> int:
        """
        Save contracts to database.
        
        Args:
            contracts: List of processed contracts
            
        Returns:
            Number of contracts saved
        """
        saved_count = 0
        
        for contract in contracts:
            try:
                # Check if exists
                existing = Symtoken.query.filter_by(
                    symbol=contract['symbol'],
                    exchange='PI42'
                ).first()
                
                if existing:
                    # Update existing
                    for key, value in contract.items():
                        setattr(existing, key, value)
                else:
                    # Create new
                    new_contract = Symtoken(**contract)
                    db.session.add(new_contract)
                
                saved_count += 1
            except Exception as e:
                print(f"Error saving {contract['symbol']}: {e}")
                continue
        
        db.session.commit()
        return saved_count
    
    def sync_contracts(self) -> Dict:
        """
        Download and sync all contracts.
        
        Returns:
            Sync result dictionary
        """
        print("Downloading contracts from Pi42...")
        raw_contracts = self.download_contracts()
        
        print(f"Processing {len(raw_contracts)} contracts...")
        processed = [self.process_contract(c) for c in raw_contracts]
        
        print("Saving to database...")
        saved = self.save_to_database(processed)
        
        return {
            'total': len(raw_contracts),
            'saved': saved,
            'status': 'success'
        }


def get_contract_info(symbol: str) -> Optional[Dict]:
    """
    Get contract information for symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Contract info dictionary or None
    """
    contract = Symtoken.query.filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()
    
    if not contract:
        return None
    
    return {
        'symbol': contract.symbol,
        'base_asset': contract.base_asset,
        'quote_asset': contract.quote_asset,
        'min_quantity': contract.min_quantity,
        'max_quantity': contract.max_quantity,
        'price_precision': contract.price_precision,
        'quantity_precision': contract.quantity_precision,
        'tick_size': contract.tick_size,
        'max_leverage': contract.max_leverage,
        'margin_assets': contract.margin_assets.split(',') if contract.margin_assets else [],
        'min_notional': contract.min_notional
    }


def search_contracts(query: str, limit: int = 10) -> List[Dict]:
    """
    Search contracts by symbol or name.
    
    Args:
        query: Search query
        limit: Maximum results
        
    Returns:
        List of matching contracts
    """
    contracts = Symtoken.query.filter(
        Symtoken.exchange == 'PI42',
        Symtoken.symbol.like(f'%{query.upper()}%')
    ).limit(limit).all()
    
    return [
        {
            'symbol': c.symbol,
            'name': c.name,
            'base_asset': c.base_asset,
            'quote_asset': c.quote_asset
        }
        for c in contracts
    ]
```

### Step 1.2: Create Contract Sync Script

**File:** `scripts/sync_pi42_contracts.py` (create new file)

```python
"""Sync Pi42 contracts to database."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from broker.pi42.api.auth_api import Pi42Auth
from broker.pi42.database.master_contract_db import Pi42MasterContract


def main():
    """Sync Pi42 contracts."""
    # Get credentials
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    
    if not api_key or not api_secret:
        print("Error: PI42_API_KEY and PI42_API_SECRET must be set in .env")
        return 1
    
    # Create auth and master contract instances
    auth = Pi42Auth(api_key, api_secret)
    master = Pi42MasterContract(auth)
    
    # Sync contracts
    try:
        result = master.sync_contracts()
        print(f"\n✓ Sync complete: {result['saved']}/{result['total']} contracts saved")
        return 0
    except Exception as e:
        print(f"\n✗ Sync failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

**Run sync:**
```bash
uv run python scripts/sync_pi42_contracts.py
```

**Verify:**
```bash
uv run python -c "
from database.symbol_db import Symtoken

contracts = Symtoken.query.filter_by(exchange='PI42').all()
print(f'Total Pi42 contracts: {len(contracts)}')

if contracts:
    btc = Symtoken.query.filter_by(symbol='BTCUSDT', exchange='PI42').first()
    if btc:
        print(f'\\nBTCUSDT contract:')
        print(f'  Base: {btc.base_asset}')
        print(f'  Quote: {btc.quote_asset}')
        print(f'  Max Leverage: {btc.max_leverage}')
        print(f'  Price Precision: {btc.price_precision}')
        print(f'  Quantity Precision: {btc.quantity_precision}')
"
```

---

## Day 3-4: Basic Order API

### Step 2.1: Create Order API Module

**File:** `broker/pi42/api/order_api.py`

```python
"""Pi42 order management API."""

import requests
from typing import Dict, Tuple, Optional
from broker.pi42.api.auth_api import create_auth_instance
from broker.pi42.api.rate_limiter import rate_limiter


def place_order_api(data: Dict, auth_token: str) -> Tuple[Dict, int]:
    """
    Place order on Pi42.
    
    Args:
        data: Order data in OpenAlgo format
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Create auth instance
        auth = create_auth_instance(auth_token)
        
        # Transform to Pi42 format
        from broker.pi42.mapping.transform_data import transform_order_data
        pi42_data = transform_order_data(data)
        
        # Rate limit check
        rate_limiter.wait_if_needed('place_order')
        
        # Sign request
        endpoint = '/v1/order/place-order'
        headers, body = auth.sign_request('POST', endpoint, body=pi42_data)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            result = response.json()
            order_id = result.get('orderId', '')
            
            return {
                'status': 'success',
                'orderid': order_id,
                'message': 'Order placed successfully'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Order failed: {response.text}"
            }, response.status_code
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Order error: {str(e)}"
        }, 500


def cancel_order_api(order_id: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Cancel order on Pi42.
    
    Args:
        order_id: Order ID to cancel
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Rate limit check
        rate_limiter.wait_if_needed('cancel_order')
        
        # Sign request
        endpoint = '/v1/order/cancel-order'
        body = {'orderId': order_id}
        headers, body = auth.sign_request('POST', endpoint, body=body)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            return {
                'status': 'success',
                'orderid': order_id,
                'message': 'Order cancelled successfully'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Cancel failed: {response.text}"
            }, response.status_code
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Cancel error: {str(e)}"
        }, 500


def get_order_book(auth_token: str) -> Tuple[Dict, int]:
    """
    Get all orders from Pi42.
    
    Args:
        auth_token: Encrypted auth token
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)
        
        # Sign request
        endpoint = '/v1/order/open-orders'
        headers, _ = auth.sign_request('GET', endpoint)
        
        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            orders = response.json()
            
            # Transform to OpenAlgo format
            from broker.pi42.mapping.order_data import map_order_data
            transformed = [map_order_data(order) for order in orders]
            
            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get orders: {response.text}"
            }, response.status_code
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500
```

### Step 2.2: Create Data Transformation Module

**File:** `broker/pi42/mapping/transform_data.py`

```python
"""Transform OpenAlgo data to Pi42 format."""

from typing import Dict


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
    
    # Add price for LIMIT orders
    if data['pricetype'] in ['LIMIT', 'SL']:
        pi42_data['price'] = float(data['price'])
    
    # Add stop price for STOP orders
    if data['pricetype'] in ['SL', 'SL-M']:
        pi42_data['stopPrice'] = float(data.get('trigger_price', data.get('price', 0)))
    
    # Add crypto-specific fields
    if 'leverage' in data:
        pi42_data['leverage'] = int(data['leverage'])
    
    if 'margin_mode' in data:
        pi42_data['marginMode'] = data['margin_mode']
    
    if 'margin_asset' in data:
        pi42_data['marginAsset'] = data['margin_asset']
    
    return pi42_data


def format_crypto_price(price: float, precision: int) -> float:
    """
    Format price to correct precision.
    
    Args:
        price: Price value
        precision: Decimal places
        
    Returns:
        Formatted price
    """
    return round(price, precision)


def format_crypto_quantity(quantity: float, precision: int) -> float:
    """
    Format quantity to correct precision.
    
    Args:
        quantity: Quantity value
        precision: Decimal places
        
    Returns:
        Formatted quantity
    """
    return round(quantity, precision)
```

### Step 2.3: Create Order Data Mapping Module

**File:** `broker/pi42/mapping/order_data.py`

```python
"""Map Pi42 order data to OpenAlgo format."""

from typing import Dict


def map_order_data(order: Dict) -> Dict:
    """
    Map Pi42 order to OpenAlgo format.
    
    Args:
        order: Pi42 order data
        
    Returns:
        OpenAlgo order data
    """
    # Map order status
    status_map = {
        'NEW': 'open',
        'PARTIALLY_FILLED': 'open',
        'FILLED': 'complete',
        'CANCELED': 'cancelled',
        'REJECTED': 'rejected',
        'EXPIRED': 'cancelled'
    }
    
    # Map order type
    type_map = {
        'MARKET': 'MARKET',
        'LIMIT': 'LIMIT',
        'STOP_MARKET': 'SL-M',
        'STOP_LIMIT': 'SL'
    }
    
    return {
        'symbol': order['symbol'],
        'exchange': 'PI42',
        'action': order['side'],
        'quantity': float(order['origQty']),
        'price': float(order.get('price', 0)),
        'trigger_price': float(order.get('stopPrice', 0)),
        'pricetype': type_map.get(order['type'], 'MARKET'),
        'product': order.get('marginMode', 'ISOLATED'),
        'orderid': order['orderId'],
        'order_status': status_map.get(order['status'], 'pending'),
        'timestamp': order.get('time', ''),
        'filled_quantity': float(order.get('executedQty', 0)),
        'pending_quantity': float(order['origQty']) - float(order.get('executedQty', 0)),
        'average_price': float(order.get('avgPrice', 0))
    }
```

### Step 2.4: Test Order Placement

**File:** `test/test_pi42_orders.py`

```python
"""Test Pi42 order placement."""

import os
from broker.pi42.api.order_api import place_order_api, cancel_order_api
from utils.encryption import encrypt_token


def test_place_market_order():
    """Test market order placement."""
    # Create test auth token
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    # Test order data
    order_data = {
        'symbol': 'BTCUSDT',
        'action': 'BUY',
        'quantity': '0.001',  # Minimum quantity
        'pricetype': 'MARKET',
        'leverage': 1,
        'margin_mode': 'ISOLATED',
        'margin_asset': 'USDT'
    }
    
    # Place order
    result, status = place_order_api(order_data, auth_token)
    
    print(f"Status: {status}")
    print(f"Result: {result}")
    
    assert status == 200
    assert result['status'] == 'success'
    assert 'orderid' in result
    
    return result['orderid']


def test_cancel_order(order_id: str):
    """Test order cancellation."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    result, status = cancel_order_api(order_id, auth_token)
    
    print(f"Cancel Status: {status}")
    print(f"Cancel Result: {result}")
    
    assert status == 200
    assert result['status'] == 'success'


if __name__ == '__main__':
    print("Testing order placement...")
    order_id = test_place_market_order()
    
    print(f"\nOrder placed: {order_id}")
    print("Note: Cancel manually if needed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_orders.py -v -s
```

---

## Day 5: Market Data API

### Step 3.1: Create Market Data Module

**File:** `broker/pi42/api/data.py`

```python
"""Pi42 market data API."""

import requests
from typing import Dict, Optional
from broker.pi42.api.auth_api import create_auth_instance


class BrokerData:
    """Pi42 market data handler."""
    
    def __init__(self, auth_token: str):
        """Initialize with auth token."""
        self.auth = create_auth_instance(auth_token)
    
    def get_quotes(self, symbol: str) -> Dict:
        """
        Get quote data for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote data dictionary
        """
        endpoint = '/v1/ticker/24hr'
        params = {'symbol': symbol}
        headers, _ = self.auth.sign_request('GET', endpoint, params=params)
        
        url = f"{self.auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get quotes: {response.text}")
        
        data = response.json()
        
        return {
            'symbol': data['symbol'],
            'exchange': 'PI42',
            'ltp': float(data['lastPrice']),
            'open': float(data['openPrice']),
            'high': float(data['highPrice']),
            'low': float(data['lowPrice']),
            'close': float(data['lastPrice']),
            'volume': float(data['volume']),
            'oi': float(data.get('openInterest', 0)),
            'mark_price': float(data.get('markPrice', data['lastPrice'])),
            'index_price': float(data.get('indexPrice', data['lastPrice'])),
            'funding_rate': float(data.get('lastFundingRate', 0))
        }
    
    def get_depth(self, symbol: str) -> Dict:
        """
        Get order book depth.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Depth data dictionary
        """
        endpoint = '/v1/depth'
        params = {'symbol': symbol, 'limit': 5}
        headers, _ = self.auth.sign_request('GET', endpoint, params=params)
        
        url = f"{self.auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get depth: {response.text}")
        
        data = response.json()
        
        return {
            'symbol': symbol,
            'exchange': 'PI42',
            'bids': [[float(p), float(q)] for p, q in data['bids']],
            'asks': [[float(p), float(q)] for p, q in data['asks']]
        }
    
    def get_history(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> list:
        """
        Get historical klines data.
        
        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d)
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
            limit: Number of klines
            
        Returns:
            List of kline data
        """
        endpoint = '/v1/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        headers, _ = self.auth.sign_request('GET', endpoint, params=params)
        
        url = f"{self.auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get history: {response.text}")
        
        return response.json()
```

### Step 3.2: Test Market Data

**File:** `test/test_pi42_data.py`

```python
"""Test Pi42 market data."""

import os
from broker.pi42.api.data import BrokerData
from utils.encryption import encrypt_token


def test_quotes():
    """Test quote data."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    data = BrokerData(auth_token)
    quotes = data.get_quotes('BTCUSDT')
    
    print("Quotes:")
    print(f"  Symbol: {quotes['symbol']}")
    print(f"  LTP: {quotes['ltp']}")
    print(f"  Mark Price: {quotes['mark_price']}")
    print(f"  Funding Rate: {quotes['funding_rate']}")
    
    assert quotes['symbol'] == 'BTCUSDT'
    assert quotes['ltp'] > 0


def test_depth():
    """Test order book depth."""
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    auth_token = encrypt_token(f"{api_key}|{api_secret}")
    
    data = BrokerData(auth_token)
    depth = data.get_depth('BTCUSDT')
    
    print("\nDepth:")
    print(f"  Bids: {len(depth['bids'])}")
    print(f"  Asks: {len(depth['asks'])}")
    print(f"  Best Bid: {depth['bids'][0]}")
    print(f"  Best Ask: {depth['asks'][0]}")
    
    assert len(depth['bids']) > 0
    assert len(depth['asks']) > 0


if __name__ == '__main__':
    test_quotes()
    test_depth()
    print("\n✓ Market data tests passed")
```

**Run test:**
```bash
uv run pytest test/test_pi42_data.py -v -s
```

---

## Week 2 Completion Checklist

- [ ] Master contract database module created
- [ ] Contract sync script working
- [ ] Pi42 contracts downloaded and saved
- [ ] Order API module implemented
- [ ] Data transformation modules created
- [ ] Order placement tested (MARKET orders)
- [ ] Order cancellation tested
- [ ] Market data API implemented
- [ ] Quotes API tested
- [ ] Depth API tested

**Verification Command:**
```bash
uv run python -c "
from database.symbol_db import Symtoken
from broker.pi42.database.master_contract_db import get_contract_info

# Check contracts
contracts = Symtoken.query.filter_by(exchange='PI42').count()
print(f'Pi42 contracts in database: {contracts}')

# Check contract info
btc_info = get_contract_info('BTCUSDT')
if btc_info:
    print(f'\\nBTCUSDT info:')
    print(f'  Max Leverage: {btc_info[\"max_leverage\"]}')
    print(f'  Min Quantity: {btc_info[\"min_quantity\"]}')
    print(f'  Price Precision: {btc_info[\"price_precision\"]}')

print('\\n✓ Week 2 basic integration complete')
"
```

---

## Phase 1 Complete!

**Achievements:**
- ✅ Core infrastructure set up
- ✅ Database schema extended
- ✅ Authentication working
- ✅ Master contracts synced
- ✅ Basic orders functional
- ✅ Market data accessible

**Next Phase:** Phase 2 - Core Trading Features
- Advanced order types (STOP orders)
- Position management
- Leverage management
- Margin operations

Continue to `PHASE-2-CORE-TRADING.md`
