# Pi42 Integration - Phase 2 Complete

## Summary

Successfully completed Phase 2 (Week 3-4) of Pi42 cryptocurrency futures exchange integration into OpenAlgo.

## Completed Tasks

### Week 3: Advanced Orders ✅

1. **STOP_MARKET and STOP_LIMIT Orders**
   - Enhanced [transform_data.py](broker/pi42/mapping/transform_data.py) with STOP order support
   - Added `stopPrice` parameter for trigger price
   - Added `timeInForce` parameter (GTC, IOC, FOK)
   - Added `reduceOnly` flag for position closing
   - Added `postOnly` flag for maker-only orders
   - Order type mapping: SL → STOP_LIMIT, SL-M → STOP_MARKET

2. **Position Management API**
   - Created [position_api.py](broker/pi42/api/position_api.py)
   - `get_positions()` - Fetch all open positions with PnL
   - `close_position()` - Close position with MARKET order
   - Position data mapping to OpenAlgo format
   - Support for LONG/SHORT/FLAT position sides
   - Liquidation price and margin tracking

3. **Smart Order Routing**
   - Created [order_routing.py](broker/pi42/utils/order_routing.py)
   - `route_order()` - Validate and optimize order parameters
   - `split_large_order()` - Split orders exceeding max quantity
   - `optimize_order_execution()` - Strategy based on urgency (LOW/NORMAL/HIGH)
   - `calculate_slippage_estimate()` - Estimate execution slippage
   - `suggest_order_improvements()` - Provide optimization suggestions
   - Automatic precision adjustment for price and quantity

### Week 4: Leverage & Margin ✅

1. **Leverage Adjustment API**
   - Created [leverage_api.py](broker/pi42/api/leverage_api.py)
   - `change_leverage()` - Adjust leverage (1-150x)
   - `change_margin_mode()` - Switch between ISOLATED/CROSS
   - `get_leverage_brackets()` - Fetch leverage tiers
   - Validation for leverage limits per contract

2. **Margin Operations**
   - `add_margin()` - Add margin to isolated position
   - `reduce_margin()` - Remove margin from isolated position
   - Type parameter: 1 = add, 2 = reduce
   - Support for both INR and USDT margin assets

3. **Position Risk Management**
   - Created [risk_management.py](broker/pi42/utils/risk_management.py)
   - `calculate_position_risk()` - Notional value, required margin, maintenance margin
   - `calculate_liquidation_price()` - Liquidation price for LONG/SHORT
   - `validate_order_risk()` - Pre-trade risk validation
   - `calculate_max_position_size()` - Max size based on risk percentage
   - `check_position_health()` - Real-time position health monitoring
   - Risk levels: LOW, MEDIUM, HIGH, CRITICAL

4. **Integration Testing**
   - Created [test_pi42_phase2.py](test/test_pi42_phase2.py)
   - Position API tests (get positions, close position)
   - Leverage API tests (change leverage, add/reduce margin)
   - Risk management tests (liquidation price, order validation, position health)
   - Order routing tests (route order, split order, optimize execution, slippage)
   - Mock-based unit tests with pytest

## Key Features Implemented

### Advanced Order Types
```python
# STOP_LIMIT order
{
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'STOP_LIMIT',
    'quantity': 0.1,
    'price': 50000,
    'stopPrice': 49000,
    'timeInForce': 'GTC'
}

# STOP_MARKET order
{
    'symbol': 'BTCUSDT',
    'side': 'SELL',
    'type': 'STOP_MARKET',
    'quantity': 0.1,
    'stopPrice': 51000,
    'reduceOnly': True
}
```

### Position Management
```python
# Get all positions
positions, status = get_positions(auth_token)

# Close position
result, status = close_position('BTCUSDT', auth_token)
```

### Leverage & Margin
```python
# Change leverage
result, status = change_leverage('BTCUSDT', 20, auth_token)

# Change margin mode
result, status = change_margin_mode('BTCUSDT', 'ISOLATED', auth_token)

# Add margin
result, status = add_margin('BTCUSDT', 100.0, auth_token)
```

### Risk Management
```python
# Calculate liquidation price
liq_price = calculate_liquidation_price(
    entry_price=50000,
    leverage=10,
    side='LONG'
)  # Returns: 45250

# Validate order risk
validation = validate_order_risk(
    symbol='BTCUSDT',
    quantity=0.1,
    price=50000,
    leverage=10,
    available_balance=10000
)

# Check position health
health = check_position_health(
    entry_price=50000,
    current_price=46000,
    quantity=1.0,
    leverage=10,
    side='LONG',
    margin=5000
)  # Returns: {'risk_level': 'CRITICAL', 'pnl': -4000, ...}
```

### Smart Order Routing
```python
# Route order with validation
routing = route_order(
    symbol='BTCUSDT',
    quantity=0.1,
    price=50000,
    order_type='LIMIT',
    side='BUY',
    available_balance=10000,
    leverage=10
)

# Split large order
chunks = split_large_order('BTCUSDT', 25.0)
# Returns: [8.333, 8.333, 8.334]

# Optimize execution
strategy = optimize_order_execution(
    symbol='BTCUSDT',
    quantity=10,
    side='BUY',
    urgency='HIGH'
)  # Returns: {'order_type': 'MARKET', 'split_order': False}
```

## File Structure

```
broker/pi42/
├── api/
│   ├── auth_api.py           # HMAC-SHA256 authentication
│   ├── rate_limiter.py       # Token bucket rate limiting
│   ├── order_api.py          # Order placement/cancellation
│   ├── position_api.py       # Position management (NEW)
│   ├── leverage_api.py       # Leverage/margin operations (NEW)
│   └── data.py               # Market data
├── database/
│   └── master_contract_db.py # Contract sync
├── mapping/
│   ├── transform_data.py     # OpenAlgo → Pi42 (ENHANCED)
│   └── order_data.py         # Pi42 → OpenAlgo
├── utils/
│   ├── risk_management.py    # Risk calculations (NEW)
│   └── order_routing.py      # Smart routing (NEW)
└── plugin.json               # Broker metadata

test/
└── test_pi42_phase2.py       # Integration tests (NEW)
```

## API Endpoints Used

### Position Management
- `GET /v1/position` - Get positions
- `POST /v1/order/place-order` - Close position (reduceOnly)

### Leverage & Margin
- `POST /v1/leverage` - Change leverage
- `POST /v1/marginType` - Change margin mode
- `POST /v1/positionMargin` - Add/reduce margin
- `GET /v1/leverageBracket` - Get leverage brackets

## Risk Management Features

### Liquidation Price Calculation
- **Long**: `entry_price × (1 - 1/leverage + maintenance_margin_rate)`
- **Short**: `entry_price × (1 + 1/leverage - maintenance_margin_rate)`

### Position Health Monitoring
- **CRITICAL**: < 5% from liquidation
- **HIGH**: 5-15% from liquidation
- **MEDIUM**: 15-30% from liquidation
- **LOW**: > 30% from liquidation

### Order Validation
- Quantity limits (min/max)
- Leverage limits (1-150x)
- Notional value limits
- Margin requirement checks

## Testing

Run Phase 2 tests:
```bash
uv run pytest test/test_pi42_phase2.py -v
```

Test coverage:
- Position API: get_positions, close_position
- Leverage API: change_leverage, change_margin_mode, add_margin, reduce_margin
- Risk Management: liquidation price, order validation, position health
- Order Routing: route_order, split_order, optimize_execution, slippage

## Next Steps - Phase 3

Phase 3 will implement WebSocket streaming:

1. **Week 5: WebSocket Foundation**
   - WebSocket connection management
   - Authentication and heartbeat
   - Message parsing and routing
   - Reconnection logic

2. **Week 6: Real-Time Data Streams**
   - Market data streams (ticker, depth, trades)
   - User data streams (orders, positions, balance)
   - Stream subscription management
   - Integration with OpenAlgo WebSocket proxy

## Notes

- All leverage operations validate against contract max_leverage
- Position closure uses MARKET orders with reduceOnly flag
- Smart routing applies precision adjustments automatically
- Risk management uses maintenance_margin_rate from contract data
- Order splitting preserves total quantity with precision rounding
- Slippage estimation supports both simple and order-book methods

---

**Status**: Phase 2 Complete ✅  
**Date**: 2026-04-18  
**Next**: Begin Phase 3 - WebSocket Streaming
