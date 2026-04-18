# Pi42 Integration - Phase 6 Complete

## Summary

Successfully completed Phase 6 (Week 11) of Pi42 cryptocurrency futures exchange integration into OpenAlgo - REST API Endpoints.

## Completed Tasks

### Week 11: REST API Endpoints ✅

1. **Leverage Management Endpoints**
   - Created [leverage.py](restx_api/leverage.py)
   - `POST /api/v1/setleverage` - Set leverage for symbol (1-150x)
   - `GET /api/v1/getleverage` - Get current leverage for symbol
   - Rate limiting: 20 requests/minute (set), 60 requests/minute (get)
   - Broker validation (Pi42 only)
   - Leverage range validation

2. **Margin Management Endpoints**
   - Created [margin_management.py](restx_api/margin_management.py)
   - `POST /api/v1/addmargin` - Add margin to position
   - `POST /api/v1/reducemargin` - Reduce margin from position
   - Rate limiting: 20 requests/minute
   - Amount validation (must be > 0)
   - Margin asset support (USDT, INR)

3. **Funding Rate Endpoints**
   - Created [funding.py](restx_api/funding.py)
   - `GET /api/v1/fundingrate` - Get current funding rate
   - `GET /api/v1/fundinghistory` - Get funding rate history
   - Rate limiting: 60 requests/minute (current), 30 requests/minute (history)
   - Time-based filtering (start_time, end_time)
   - Configurable limit (default: 100 records)

4. **Liquidation Price Calculator Endpoint**
   - Created [liquidation.py](restx_api/liquidation.py)
   - `POST /api/v1/liquidationprice` - Calculate liquidation price
   - Supports LONG and SHORT positions
   - Distance percentage calculation
   - Risk level determination (low, medium, high, critical)
   - Rate limiting: 60 requests/minute

5. **Contract Information Endpoint**
   - Created [contract_info.py](restx_api/contract_info.py)
   - `GET /api/v1/contractinfo` - Get contract specifications
   - Single symbol or all contracts
   - Returns: min/max quantity, precision, tick size, max leverage
   - Rate limiting: 60 requests/minute

6. **Split TP/SL Endpoint**
   - Created [split_tpsl.py](restx_api/split_tpsl.py)
   - `POST /api/v1/splittakeprofit` - Set multiple TP/SL levels
   - Multiple take profit levels
   - Multiple stop loss levels
   - Automatic position detection
   - Reduce-only orders
   - Rate limiting: 20 requests/minute

7. **Integration Tests**
   - Created [test_pi42_phase6.py](test/test_pi42_phase6.py)
   - Comprehensive test coverage for all endpoints
   - Mock-based unit tests
   - Success and error case testing

## API Endpoint Reference

### 1. Set Leverage

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
    "leverage": 10
  }
}
```

### 2. Get Leverage

**Endpoint:** `GET /api/v1/getleverage?apikey=xxx&symbol=BTCUSDT`

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "leverage": 10,
    "margin_mode": "ISOLATED",
    "max_leverage": 150
  }
}
```

### 3. Add Margin

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
    "new_margin": 2600
  }
}
```

### 4. Reduce Margin

**Endpoint:** `POST /api/v1/reducemargin`

**Request:**
```json
{
  "apikey": "your_api_key",
  "symbol": "BTCUSDT",
  "amount": 50
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Reduced 50 USDT margin from BTCUSDT position",
  "data": {
    "symbol": "BTCUSDT",
    "new_margin": 2450
  }
}
```

### 5. Get Funding Rate

**Endpoint:** `GET /api/v1/fundingrate?apikey=xxx&symbol=BTCUSDT`

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

### 6. Get Funding History

**Endpoint:** `GET /api/v1/fundinghistory?apikey=xxx&symbol=BTCUSDT&limit=50`

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "symbol": "BTCUSDT",
      "income": -0.5,
      "time": 1234567890,
      "income_type": "FUNDING_FEE"
    }
  ]
}
```

### 7. Calculate Liquidation Price

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
    "symbol": "BTCUSDT",
    "entry_price": 50000,
    "liquidation_price": 45250.0,
    "distance_percentage": 9.5,
    "risk_level": "medium",
    "leverage": 10,
    "side": "LONG"
  }
}
```

### 8. Get Contract Info

**Endpoint:** `GET /api/v1/contractinfo?apikey=xxx&symbol=BTCUSDT`

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "base_asset": "BTC",
    "quote_asset": "USDT",
    "min_quantity": 0.001,
    "max_quantity": 1000,
    "price_precision": 2,
    "quantity_precision": 3,
    "tick_size": 0.01,
    "max_leverage": 150,
    "margin_assets": ["USDT", "INR"],
    "min_notional": 10
  }
}
```

### 9. Set Split TP/SL

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
  "message": "Split TP/SL set successfully for BTCUSDT",
  "data": {
    "symbol": "BTCUSDT",
    "tp_orders": ["order_id_1", "order_id_2"],
    "sl_orders": ["order_id_3"],
    "tp_levels_count": 2,
    "sl_levels_count": 1
  }
}
```

## File Structure

```
restx_api/
├── leverage.py              # Leverage management endpoints (NEW)
├── margin_management.py     # Margin management endpoints (NEW)
├── funding.py               # Funding rate endpoints (NEW)
├── liquidation.py           # Liquidation calculator endpoint (NEW)
├── contract_info.py         # Contract info endpoint (NEW)
└── split_tpsl.py            # Split TP/SL endpoint (NEW)

test/
└── test_pi42_phase6.py      # Phase 6 API tests (NEW)
```

## Rate Limiting

All endpoints include rate limiting to comply with Pi42 API limits:

| Endpoint | Rate Limit |
|----------|------------|
| `/setleverage` | 20 per minute |
| `/getleverage` | 60 per minute |
| `/addmargin` | 20 per minute |
| `/reducemargin` | 20 per minute |
| `/fundingrate` | 60 per minute |
| `/fundinghistory` | 30 per minute |
| `/liquidationprice` | 60 per minute |
| `/contractinfo` | 60 per minute |
| `/splittakeprofit` | 20 per minute |

## Error Handling

All endpoints include comprehensive error handling:

### Common Errors

```json
{
  "status": "error",
  "message": "Invalid API key"
}
```

```json
{
  "status": "error",
  "message": "Leverage management only available for crypto futures (Pi42)"
}
```

```json
{
  "status": "error",
  "message": "Leverage must be between 1 and 150"
}
```

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid API key)
- `404` - Not Found (symbol/position not found)
- `500` - Internal Server Error

## Testing

Run Phase 6 tests:
```bash
uv run pytest test/test_pi42_phase6.py -v
```

Test coverage:
- Leverage API: set/get leverage with validation
- Margin API: add/reduce margin with validation
- Funding API: current rate and history
- Liquidation API: LONG/SHORT calculations
- Contract Info API: single and all contracts
- Split TP/SL API: multiple levels with position detection

## Integration Summary

### Phases 1-6 Complete ✅

**Phase 1**: Core Architecture & Basic Integration
- Database schema extensions
- Broker type detection
- Authentication & rate limiting
- Master contract sync (692 contracts)
- Order API & market data

**Phase 2**: Advanced Orders & Risk Management
- STOP_MARKET and STOP_LIMIT orders
- Position management API
- Leverage & margin operations
- Risk management utilities
- Smart order routing

**Phase 3**: WebSocket Streaming
- WebSocket connection manager
- Market data streams (ticker, depth, trades, kline)
- User data streams (orders, positions, balance)
- OpenAlgo WebSocket proxy integration

**Phase 4**: Funds & Account Management
- Account balance API
- Margin information
- Wallet transfers
- Transaction history
- Trading fees & permissions
- Position mode management

**Phase 5**: Frontend Development
- 6 crypto-specific React components
- Zustand state management
- WebSocket event handlers
- Comprehensive component tests

**Phase 6**: REST API Endpoints
- 6 new API endpoint modules
- Leverage management (set/get)
- Margin management (add/reduce)
- Funding rate (current/history)
- Liquidation calculator
- Contract information
- Split TP/SL
- Comprehensive API tests

## Next Steps - Phase 7

Phase 7 will implement comprehensive testing and QA:

1. **Week 12: Testing & QA**
   - Unit tests (80%+ coverage)
   - Integration tests (all flows)
   - E2E tests (Playwright)
   - Load testing (100+ concurrent users)
   - UAT & bug fixes

---

**Status**: Phase 6 Complete ✅  
**Date**: 2026-04-18  
**Next**: Begin Phase 7 - Testing & Quality Assurance
