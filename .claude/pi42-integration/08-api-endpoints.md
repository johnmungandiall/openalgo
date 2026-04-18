# Pi42 API Endpoints Implementation Plan

## Overview

This document details all new and modified API endpoints required for Pi42 crypto futures integration into OpenAlgo's REST API.

## New API Endpoints

### 1. Leverage Management

#### Set Leverage
**Endpoint:** `POST /api/v1/setleverage`

**Request:**
```json
{
  "apikey": "your_api_key",
  "symbol": "BTCUSDT",
  "leverage": 10
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Leverage set to 10x for BTCUSDT",
  "data": {
    "symbol": "BTCUSDT",
    "leverage": 10,
    "margin_mode": "ISOLATED"
  }
}
```

**Implementation:** `restx_api/leverage.py`

```python
from flask import request
from flask_restx import Namespace, Resource, fields

from broker.pi42.api.order_api import set_leverage
from database.auth_db import get_auth_token_broker
from utils.api_utils import validate_api_key

api = Namespace('leverage', description='Leverage management operations')

leverage_model = api.model('SetLeverage', {
    'apikey': fields.String(required=True, description='API Key'),
    'symbol': fields.String(required=True, description='Trading symbol'),
    'leverage': fields.Integer(required=True, description='Leverage (1-25)')
})

@api.route('/setleverage')
class SetLeverage(Resource):
    @api.doc(description='Set leverage for symbol')
    @api.expect(leverage_model)
    def post(self):
        """Set leverage for crypto futures position."""
        data = request.json
        
        # Validate API key
        user_id = validate_api_key(data['apikey'])
        if not user_id:
            return {'status': 'error', 'message': 'Invalid API key'}, 401
        
        # Get auth token
        auth_token, broker = get_auth_token_broker(user_id)
        
        if broker != 'pi42':
            return {
                'status': 'error',
                'message': 'Leverage management only available for crypto futures'
            }, 400
        
        # Validate leverage
        leverage = data['leverage']
        if not 1 <= leverage <= 25:
            return {
                'status': 'error',
                'message': 'Leverage must be between 1 and 25'
            }, 400
        
        # Set leverage
        result, status_code = set_leverage(
            data['symbol'],
            leverage,
            auth_token
        )
        
        return result, status_code
```

#### Get Leverage
**Endpoint:** `GET /api/v1/getleverage`

**Query Parameters:**
- `apikey`: API key
- `symbol`: Trading symbol

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "leverage": 10,
    "margin_mode": "ISOLATED",
    "max_leverage": 25
  }
}
```

### 2. Margin Management

#### Add Margin
**Endpoint:** `POST /api/v1/addmargin`

**Request:**
```json
{
  "apikey": "your_api_key",
  "symbol": "BTCUSDT",
  "amount": 100,
  "margin_asset": "USDT"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Added 100 USDT margin to BTCUSDT position",
  "data": {
    "symbol": "BTCUSDT",
    "new_margin": 2600,
    "new_liquidation_price": 44500
  }
}
```

**Implementation:** `restx_api/margin_management.py`

```python
from flask import request
from flask_restx import Namespace, Resource, fields

from broker.pi42.api.order_api import add_margin, reduce_margin
from database.auth_db import get_auth_token_broker
from utils.api_utils import validate_api_key

api = Namespace('margin', description='Margin management operations')

add_margin_model = api.model('AddMargin', {
    'apikey': fields.String(required=True),
    'symbol': fields.String(required=True),
    'amount': fields.Float(required=True),
    'margin_asset': fields.String(required=True, description='USDT or INR')
})

reduce_margin_model = api.model('ReduceMargin', {
    'apikey': fields.String(required=True),
    'symbol': fields.String(required=True),
    'amount': fields.Float(required=True)
})

@api.route('/addmargin')
class AddMargin(Resource):
    @api.doc(description='Add margin to position')
    @api.expect(add_margin_model)
    def post(self):
        """Add margin to crypto futures position."""
        data = request.json
        
        user_id = validate_api_key(data['apikey'])
        if not user_id:
            return {'status': 'error', 'message': 'Invalid API key'}, 401
        
        auth_token, broker = get_auth_token_broker(user_id)
        
        if broker != 'pi42':
            return {
                'status': 'error',
                'message': 'Margin management only for crypto futures'
            }, 400
        
        result, status_code = add_margin(
            data['symbol'],
            data['amount'],
            data['margin_asset'],
            auth_token
        )
        
        return result, status_code


@api.route('/reducemargin')
class ReduceMargin(Resource):
    @api.doc(description='Reduce margin from position')
    @api.expect(reduce_margin_model)
    def post(self):
        """Reduce margin from crypto futures position."""
        data = request.json
        
        user_id = validate_api_key(data['apikey'])
        if not user_id:
            return {'status': 'error', 'message': 'Invalid API key'}, 401
        
        auth_token, broker = get_auth_token_broker(user_id)
        
        if broker != 'pi42':
            return {
                'status': 'error',
                'message': 'Margin management only for crypto futures'
            }, 400
        
        result, status_code = reduce_margin(
            data['symbol'],
            data['amount'],
            auth_token
        )
        
        return result, status_code
```

### 3. Split TP/SL

**Endpoint:** `POST /api/v1/splittakeprofit`

**Request:**
```json
{
  "apikey": "your_api_key",
  "symbol": "BTCUSDT",
  "tp_levels": [
    {"price": 52000, "quantity": 0.2},
    {"price": 53000, "quantity": 0.3}
  ],
  "sl_levels": [
    {"price": 48000, "quantity": 0.5}
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Split TP/SL set successfully",
  "data": {
    "tp_orders": ["order_id_1", "order_id_2"],
    "sl_orders": ["order_id_3"]
  }
}
```

**Implementation:** `restx_api/split_tpsl.py`

### 4. Funding Rate

**Endpoint:** `GET /api/v1/fundingrate`

**Query Parameters:**
- `apikey`: API key
- `symbol`: Trading symbol

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "funding_rate": 0.0001,
    "next_funding_time": 1234567890,
    "mark_price": 50000,
    "index_price": 50010
  }
}
```

**Implementation:** `restx_api/funding.py`

```python
from flask import request
from flask_restx import Namespace, Resource

from broker.pi42.api.data import BrokerData
from database.auth_db import get_auth_token_broker
from utils.api_utils import validate_api_key

api = Namespace('funding', description='Funding rate operations')

@api.route('/fundingrate')
class FundingRate(Resource):
    @api.doc(description='Get current funding rate')
    @api.param('apikey', 'API Key', required=True)
    @api.param('symbol', 'Trading symbol', required=True)
    def get(self):
        """Get current funding rate for symbol."""
        apikey = request.args.get('apikey')
        symbol = request.args.get('symbol')
        
        user_id = validate_api_key(apikey)
        if not user_id:
            return {'status': 'error', 'message': 'Invalid API key'}, 401
        
        auth_token, broker = get_auth_token_broker(user_id)
        
        if broker != 'pi42':
            return {
                'status': 'error',
                'message': 'Funding rate only for crypto futures'
            }, 400
        
        broker_data = BrokerData(auth_token)
        funding_data = broker_data.get_funding_rate(symbol)
        
        return {
            'status': 'success',
            'data': funding_data
        }


@api.route('/fundinghistory')
class FundingHistory(Resource):
    @api.doc(description='Get funding rate history')
    @api.param('apikey', 'API Key', required=True)
    @api.param('symbol', 'Trading symbol', required=True)
    @api.param('limit', 'Number of records', default=100)
    def get(self):
        """Get funding rate history for symbol."""
        apikey = request.args.get('apikey')
        symbol = request.args.get('symbol')
        limit = int(request.args.get('limit', 100))
        
        user_id = validate_api_key(apikey)
        if not user_id:
            return {'status': 'error', 'message': 'Invalid API key'}, 401
        
        from broker.pi42.database.master_contract_db import get_funding_history
        
        history = get_funding_history(symbol, limit)
        
        return {
            'status': 'success',
            'data': history
        }
```

### 5. Liquidation Price Calculator

**Endpoint:** `POST /api/v1/liquidationprice`

**Request:**
```json
{
  "apikey": "your_api_key",
  "symbol": "BTCUSDT",
  "entry_price": 50000,
  "quantity": 0.5,
  "leverage": 10,
  "side": "LONG"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "liquidation_price": 45000,
    "distance_percentage": 10.0,
    "risk_level": "medium"
  }
}
```

**Implementation:** `restx_api/liquidation.py`

### 6. Contract Specifications

**Endpoint:** `GET /api/v1/contractinfo`

**Query Parameters:**
- `apikey`: API key
- `symbol`: Trading symbol (optional, returns all if not provided)

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "symbol": "BTCUSDT",
      "base_asset": "BTC",
      "quote_asset": "USDT",
      "min_quantity": 0.001,
      "max_quantity": 1000,
      "price_precision": 2,
      "quantity_precision": 3,
      "tick_size": 0.01,
      "max_leverage": 25,
      "margin_assets": ["USDT", "INR"],
      "min_notional": 10
    }
  ]
}
```

**Implementation:** `restx_api/contract_info.py`

## Modified API Endpoints

### 1. Place Order - Extended

**Endpoint:** `POST /api/v1/placeorder`

**Extended Request (Crypto):**
```json
{
  "apikey": "your_api_key",
  "symbol": "BTCUSDT",
  "action": "BUY",
  "quantity": "0.5",
  "pricetype": "LIMIT",
  "price": "50000",
  "leverage": 10,
  "margin_mode": "ISOLATED",
  "margin_asset": "USDT",
  "stop_price": "49000"
}
```

**Modifications in:** `restx_api/place_order.py`

```python
# Add crypto-specific fields to model
place_order_model = api.model('PlaceOrder', {
    # ... existing fields ...
    'leverage': fields.Integer(description='Leverage (crypto only)', default=1),
    'margin_mode': fields.String(description='ISOLATED or CROSS (crypto only)'),
    'margin_asset': fields.String(description='USDT or INR (crypto only)'),
    'stop_price': fields.Float(description='Stop price for STOP orders')
})

# In place order logic, detect broker type
if broker == 'pi42':
    # Include crypto-specific fields
    order_data['leverage'] = data.get('leverage', 1)
    order_data['margin_mode'] = data.get('margin_mode', 'ISOLATED')
    order_data['margin_asset'] = data.get('margin_asset', 'USDT')
    if 'stop_price' in data:
        order_data['trigger_price'] = data['stop_price']
```

### 2. Positions - Extended

**Endpoint:** `GET /api/v1/positionbook`

**Extended Response (Crypto):**
```json
{
  "status": "success",
  "data": [
    {
      "symbol": "BTCUSDT",
      "exchange": "PI42",
      "side": "LONG",
      "quantity": 0.5,
      "entry_price": 50000,
      "mark_price": 51000,
      "liquidation_price": 45000,
      "unrealized_pnl": 500,
      "realized_pnl": 0,
      "margin": 2500,
      "leverage": 10,
      "margin_mode": "ISOLATED",
      "roe": 20.0,
      "funding_fee": -2.5
    }
  ]
}
```

**Modifications in:** `restx_api/positionbook.py`

### 3. Quotes - Extended

**Endpoint:** `GET /api/v1/quotes`

**Extended Response (Crypto):**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "exchange": "PI42",
    "ltp": 50000,
    "mark_price": 50010,
    "index_price": 50005,
    "funding_rate": 0.0001,
    "open": 49500,
    "high": 51000,
    "low": 49000,
    "volume": 1234.56,
    "oi": 5000
  }
}
```

**Modifications in:** `restx_api/quotes.py`

## API Documentation Updates

### Swagger/OpenAPI Spec

Update `restx_api/__init__.py` to register new namespaces:

```python
from restx_api.leverage import api as leverage_api
from restx_api.margin_management import api as margin_api
from restx_api.split_tpsl import api as split_tpsl_api
from restx_api.funding import api as funding_api
from restx_api.liquidation import api as liquidation_api
from restx_api.contract_info import api as contract_info_api

# Register namespaces
api.add_namespace(leverage_api, path='/api/v1')
api.add_namespace(margin_api, path='/api/v1')
api.add_namespace(split_tpsl_api, path='/api/v1')
api.add_namespace(funding_api, path='/api/v1')
api.add_namespace(liquidation_api, path='/api/v1')
api.add_namespace(contract_info_api, path='/api/v1')
```

## Rate Limiting

Add crypto-specific rate limits in `limiter.py`:

```python
# Pi42 rate limits
PI42_RATE_LIMITS = {
    'place_order': '20 per second',
    'cancel_order': '30 per minute',
    'default': '60 per minute'
}

# Apply rate limits based on broker
@limiter.limit(lambda: get_broker_rate_limit('place_order'))
def place_order_endpoint():
    pass
```

## Error Handling

Add crypto-specific error codes:

```python
CRYPTO_ERROR_CODES = {
    'INSUFFICIENT_MARGIN': 'Insufficient margin for position',
    'LEVERAGE_TOO_HIGH': 'Leverage exceeds maximum allowed',
    'LIQUIDATION_RISK': 'Position at risk of liquidation',
    'FUNDING_FEE_FAILED': 'Funding fee deduction failed',
    'INVALID_MARGIN_ASSET': 'Invalid margin asset',
    'POSITION_NOT_FOUND': 'Position not found',
    'MARGIN_LOCKED': 'Margin is locked in open orders'
}
```

## Testing

### API Tests

```python
# test/test_crypto_api.py

def test_set_leverage():
    """Test leverage setting."""
    response = client.post('/api/v1/setleverage', json={
        'apikey': test_api_key,
        'symbol': 'BTCUSDT',
        'leverage': 10
    })
    
    assert response.status_code == 200
    assert response.json['status'] == 'success'


def test_add_margin():
    """Test margin addition."""
    response = client.post('/api/v1/addmargin', json={
        'apikey': test_api_key,
        'symbol': 'BTCUSDT',
        'amount': 100,
        'margin_asset': 'USDT'
    })
    
    assert response.status_code == 200


def test_funding_rate():
    """Test funding rate retrieval."""
    response = client.get('/api/v1/fundingrate', params={
        'apikey': test_api_key,
        'symbol': 'BTCUSDT'
    })
    
    assert response.status_code == 200
    assert 'funding_rate' in response.json['data']


def test_crypto_place_order():
    """Test crypto order placement."""
    response = client.post('/api/v1/placeorder', json={
        'apikey': test_api_key,
        'symbol': 'BTCUSDT',
        'action': 'BUY',
        'quantity': '0.001',
        'pricetype': 'MARKET',
        'leverage': 5,
        'margin_mode': 'ISOLATED',
        'margin_asset': 'USDT'
    })
    
    assert response.status_code == 200
```

## API Client Libraries

Update official SDKs to support crypto endpoints:

### Python SDK Example

```python
# openalgo-python-library update

class OpenAlgoCrypto:
    """Crypto-specific methods."""
    
    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for symbol."""
        return self.client.post('/api/v1/setleverage', {
            'symbol': symbol,
            'leverage': leverage
        })
    
    def add_margin(self, symbol: str, amount: float, margin_asset: str = 'USDT'):
        """Add margin to position."""
        return self.client.post('/api/v1/addmargin', {
            'symbol': symbol,
            'amount': amount,
            'margin_asset': margin_asset
        })
    
    def get_funding_rate(self, symbol: str):
        """Get current funding rate."""
        return self.client.get('/api/v1/fundingrate', {
            'symbol': symbol
        })
```

## Documentation

Create comprehensive API documentation:

1. **Crypto Trading Guide** - How to use crypto-specific endpoints
2. **Leverage Management** - Best practices for leverage
3. **Margin Management** - Adding/reducing margin
4. **Funding Rates** - Understanding funding fees
5. **Risk Management** - Liquidation prevention

## Next Steps

1. Implement all new API endpoints
2. Modify existing endpoints for crypto support
3. Add rate limiting
4. Create comprehensive tests
5. Update API documentation
6. Update SDK libraries
7. Create usage examples
