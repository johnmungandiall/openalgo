# Pi42 Integration - Quick Start Guide

## Overview

This quick start guide provides a condensed overview for developers to quickly understand and begin implementing Pi42 crypto futures integration into OpenAlgo.

## What is Pi42?

Pi42 is a cryptocurrency futures exchange offering perpetual futures contracts with:
- **24/7 Trading**: No market hours restrictions
- **High Leverage**: Up to 25x leverage
- **Multi-Asset Margin**: USDT and INR support
- **Perpetual Contracts**: No expiry dates
- **Funding Fees**: Every 8 hours
- **Real-Time WebSocket**: Order and position updates

## Key Differences from Stock Trading

### 1. No Exchange Parameter
```python
# Stock Trading
symbol = "SBIN"
exchange = "NSE"  # Required

# Crypto Trading (Pi42)
symbol = "BTCUSDT"
exchange = "PI42"  # Always Pi42, optional
```

### 2. Leverage Instead of Product Type
```python
# Stock Trading
product = "MIS"  # or NRML, CNC

# Crypto Trading
margin_mode = "ISOLATED"  # or CROSS
leverage = 10  # 1x to 25x
```

### 3. Additional Position Fields
```python
# Stock Position
{
    "symbol": "SBIN",
    "quantity": 100,
    "average_price": 625.50
}

# Crypto Position
{
    "symbol": "BTCUSDT",
    "side": "LONG",
    "quantity": 0.5,
    "entry_price": 50000,
    "mark_price": 51000,
    "liquidation_price": 45000,  # NEW
    "unrealized_pnl": 500,        # NEW
    "margin": 2500,               # NEW
    "leverage": 10,               # NEW
    "funding_fee": -2.5           # NEW
}
```

## Quick Implementation Checklist

### Phase 1: Core Setup (Week 1-2)
```
□ Add broker_type field to database
□ Extend symtoken table with crypto fields
□ Create new crypto tables (funding_rates, liquidations, etc.)
□ Implement Pi42Auth class with HMAC-SHA256
□ Create master contract download from API
□ Implement basic order placement (MARKET, LIMIT)
```

### Phase 2: Trading Features (Week 3-4)
```
□ Implement STOP orders (STOP_MARKET, STOP_LIMIT)
□ Add position management with PnL calculations
□ Implement leverage management API
□ Add margin add/reduce functionality
□ Complete data transformations
```

### Phase 3: Advanced Features (Week 5-6)
```
□ Implement split TP/SL
□ Add funding rate tracking
□ Create liquidation price calculator
□ Implement historical klines API
□ Add portfolio analytics
```

### Phase 4: Real-Time (Week 7-8)
```
□ Implement WebSocket adapter
□ Add order/position update streams
□ Create alert system (margin call, liquidation)
□ Integrate with OpenAlgo WebSocket proxy
```

### Phase 5: Frontend (Week 9-10)
```
□ Create LeverageSlider component
□ Create MarginModeToggle component
□ Create CryptoPositionCard component
□ Create FundingRateDisplay component
□ Modify order form for crypto
```

### Phase 6: API & Testing (Week 11-12)
```
□ Implement all new API endpoints
□ Write comprehensive tests
□ Conduct load testing
□ Fix bugs and optimize
```

## File Structure

```
broker/pi42/
├── __init__.py
├── plugin.json                    # Broker metadata
├── api/
│   ├── __init__.py
│   ├── auth_api.py               # HMAC-SHA256 authentication
│   ├── order_api.py              # Order management
│   ├── data.py                   # Market data (quotes, depth, klines)
│   └── funds.py                  # Wallet/balance
├── database/
│   └── master_contract_db.py     # Contract specifications
├── mapping/
│   ├── order_data.py             # Pi42 → OpenAlgo transformations
│   └── transform_data.py         # OpenAlgo → Pi42 transformations
└── streaming/
    └── pi42_adapter.py           # WebSocket adapter

restx_api/
├── leverage.py                    # NEW: Leverage management
├── margin_management.py           # NEW: Margin add/reduce
├── split_tpsl.py                 # NEW: Split TP/SL
├── funding.py                    # NEW: Funding rate
├── liquidation.py                # NEW: Liquidation calculator
└── contract_info.py              # NEW: Contract specifications

frontend/src/components/crypto/
├── LeverageSlider.tsx            # NEW: Leverage control
├── MarginModeToggle.tsx          # NEW: Margin mode selector
├── MarginAssetSelector.tsx       # NEW: Asset selector
├── CryptoPositionCard.tsx        # NEW: Enhanced position card
├── FundingRateDisplay.tsx        # NEW: Funding rate widget
└── SplitTPSL.tsx                 # NEW: Split TP/SL interface
```

## Essential Code Snippets

### 1. Authentication
```python
# broker/pi42/api/auth_api.py
import hmac
import hashlib

def generate_signature(data: str, secret: str) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
```

### 2. Place Order
```python
# broker/pi42/api/order_api.py
def place_order_api(data: dict, auth_token: str):
    # Transform OpenAlgo → Pi42 format
    pi42_data = {
        "symbol": data["symbol"],
        "side": data["action"],
        "type": map_order_type(data["pricetype"]),
        "quantity": float(data["quantity"]),
        "leverage": int(data.get("leverage", 1)),
        "marginAsset": data.get("margin_asset", "USDT")
    }
    
    # Sign and send request
    auth = create_auth_instance(auth_token)
    headers, body = auth.sign_request("POST", "/v1/order/place-order", body=pi42_data)
    response = client.post(url, headers=headers, json=body)
    
    return response, response.json(), orderid
```

### 3. Calculate Liquidation Price
```python
# broker/pi42/mapping/transform_data.py
def calculate_liquidation_price(entry_price: float, leverage: int, side: str) -> float:
    margin_ratio = 0.01  # 1% maintenance margin
    
    if side == "LONG":
        return entry_price * (1 - 1/leverage + margin_ratio)
    else:
        return entry_price * (1 + 1/leverage - margin_ratio)
```

### 4. WebSocket Connection
```python
# broker/pi42/streaming/pi42_adapter.py
async def connect(self):
    # Create listen key
    self.listen_key, error = create_listen_key(self.auth_token)
    
    # Connect to authenticated stream
    auth_url = f"{self.auth_ws_url}?listenKey={self.listen_key}"
    self.auth_ws = await websockets.connect(auth_url)
    
    # Start message handlers
    asyncio.create_task(self._handle_auth_messages())
```

### 5. Frontend Leverage Slider
```typescript
// frontend/src/components/crypto/LeverageSlider.tsx
export function LeverageSlider({ value, onChange, entryPrice, quantity, side }) {
  const [liquidationPrice, setLiquidationPrice] = useState(0);
  
  useEffect(() => {
    if (entryPrice && quantity && value > 0) {
      const liqPrice = side === 'LONG'
        ? entryPrice * (1 - 1/value + 0.01)
        : entryPrice * (1 + 1/value - 0.01);
      setLiquidationPrice(liqPrice);
    }
  }, [value, entryPrice, quantity, side]);
  
  return (
    <div>
      <Slider value={[value]} onValueChange={(v) => onChange(v[0])} min={1} max={25} />
      <div>Liquidation Price: ${liquidationPrice.toFixed(2)}</div>
    </div>
  );
}
```

## API Examples

### Place Crypto Order
```bash
curl -X POST http://localhost:5000/api/v1/placeorder \
  -H "Content-Type: application/json" \
  -d '{
    "apikey": "your_api_key",
    "symbol": "BTCUSDT",
    "action": "BUY",
    "quantity": "0.5",
    "pricetype": "LIMIT",
    "price": "50000",
    "leverage": 10,
    "margin_mode": "ISOLATED",
    "margin_asset": "USDT"
  }'
```

### Set Leverage
```bash
curl -X POST http://localhost:5000/api/v1/setleverage \
  -H "Content-Type: application/json" \
  -d '{
    "apikey": "your_api_key",
    "symbol": "BTCUSDT",
    "leverage": 10
  }'
```

### Add Margin
```bash
curl -X POST http://localhost:5000/api/v1/addmargin \
  -H "Content-Type: application/json" \
  -d '{
    "apikey": "your_api_key",
    "symbol": "BTCUSDT",
    "amount": 100,
    "margin_asset": "USDT"
  }'
```

### Get Funding Rate
```bash
curl "http://localhost:5000/api/v1/fundingrate?apikey=your_api_key&symbol=BTCUSDT"
```

## Testing Commands

```bash
# Backend unit tests
uv run pytest test/test_pi42_*.py -v

# Frontend unit tests
cd frontend && npm test

# Integration tests
uv run pytest test/integration/test_pi42_*.py -v

# E2E tests
cd frontend && npm run e2e

# Load tests
locust -f test/load/locustfile.py --host=http://localhost:5000
```

## Common Pitfalls & Solutions

### 1. Signature Generation
**Problem**: Authentication fails with invalid signature
**Solution**: Ensure timestamp is in milliseconds, sign the exact request body

### 2. Precision Errors
**Problem**: Orders rejected due to precision
**Solution**: Use `format_crypto_price()` and `format_crypto_quantity()`

### 3. Liquidation Calculation
**Problem**: Incorrect liquidation price
**Solution**: Use mark price, not last price; account for maintenance margin

### 4. WebSocket Disconnections
**Problem**: WebSocket drops frequently
**Solution**: Implement automatic reconnection, refresh listen key every 30 minutes

### 5. Funding Fee Tracking
**Problem**: Funding fees not recorded
**Solution**: Store funding events in database, emit notifications

## Environment Variables

Add to `.env`:
```bash
# Pi42 Configuration
PI42_API_KEY=your_api_key
PI42_API_SECRET=your_api_secret
PI42_BASE_URL=https://fapi.pi42.com
PI42_WS_URL=wss://fawss-uds.pi42.com/auth-stream

# Add pi42 to valid brokers
VALID_BROKERS=zerodha,dhan,pi42
```

## Database Migration

```sql
-- Add crypto fields to symtoken
ALTER TABLE symtoken ADD COLUMN broker_type VARCHAR(20) DEFAULT 'IN_stock';
ALTER TABLE symtoken ADD COLUMN min_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN max_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN price_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN quantity_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN margin_assets TEXT;
ALTER TABLE symtoken ADD COLUMN max_leverage INTEGER;
ALTER TABLE symtoken ADD COLUMN base_asset VARCHAR(10);
ALTER TABLE symtoken ADD COLUMN quote_asset VARCHAR(10);

-- Create funding rates table
CREATE TABLE funding_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(50) NOT NULL,
    funding_rate FLOAT NOT NULL,
    funding_time DATETIME NOT NULL,
    mark_price FLOAT,
    index_price FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create liquidations table
CREATE TABLE liquidations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity FLOAT NOT NULL,
    liquidation_price FLOAT NOT NULL,
    loss FLOAT NOT NULL,
    timestamp DATETIME NOT NULL
);
```

## Resources

### Documentation
- **Pi42 API Docs**: https://docs.pi42.com/
- **OpenAlgo Docs**: https://docs.openalgo.in/
- **This Integration Plan**: `.claude/pi42-integration/`

### Support
- **Pi42 Support**: support@pi42.com
- **OpenAlgo Discord**: https://discord.com/invite/UPh7QPsNhP
- **GitHub Issues**: https://github.com/marketcalls/openalgo/issues

### Tools
- **Postman Collection**: Create for Pi42 API testing
- **WebSocket Tester**: Use for testing WebSocket connections
- **Locust**: For load testing

## Next Steps

1. **Review all planning documents** in `.claude/pi42-integration/`
2. **Set up Pi42 test account** and get API credentials
3. **Start with Phase 1** (Foundation) from the roadmap
4. **Test each component** thoroughly before moving to next phase
5. **Document any deviations** from the plan
6. **Seek help** when needed via Discord or GitHub

## Success Metrics

Track these metrics during implementation:
- ✅ All unit tests passing (>80% coverage)
- ✅ All integration tests passing
- ✅ Order execution < 500ms
- ✅ WebSocket latency < 100ms
- ✅ Zero critical bugs in production
- ✅ Positive user feedback

---

**Remember**: This is a complex integration. Take it phase by phase, test thoroughly, and don't hesitate to ask for help. Good luck! 🚀
