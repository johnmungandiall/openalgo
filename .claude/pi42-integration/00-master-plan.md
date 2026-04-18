# Pi42 Crypto Exchange Integration - Master Plan

## Overview

This document outlines the comprehensive plan for integrating Pi42 cryptocurrency futures exchange into OpenAlgo. Pi42 is fundamentally different from existing stock brokers as it deals with crypto futures trading, requiring significant architectural considerations.

## Critical Differences: Crypto Futures vs Stock Trading

### 1. Market Structure Differences

| Aspect | Stock Trading (Existing) | Crypto Futures (Pi42) |
|--------|-------------------------|----------------------|
| **Market Type** | Spot equity, F&O | Perpetual futures only |
| **Trading Hours** | 9:15 AM - 3:30 PM (IST) | 24/7/365 |
| **Exchanges** | NSE, BSE, NFO, BFO, MCX | Single exchange (Pi42) |
| **Symbols** | SBIN, NIFTY24JAN24000CE | BTCUSDT, ETHUSDT |
| **Expiry** | Monthly/Weekly expiry | Perpetual (no expiry) |
| **Settlement** | T+2 for equity | Instant settlement |
| **Margin Assets** | INR only | INR, USDT (multi-asset) |

### 2. Order & Position Differences

| Feature | Stock Trading | Crypto Futures (Pi42) |
|---------|--------------|----------------------|
| **Leverage** | Fixed by exchange | User-configurable (1x-25x) |
| **Margin Mode** | Product type (MIS/NRML/CNC) | Isolated/Cross margin |
| **Position Types** | Long/Short in F&O only | Always Long/Short (futures) |
| **Order Types** | MARKET, LIMIT, SL, SL-M | MARKET, LIMIT, STOP_MARKET, STOP_LIMIT |
| **TP/SL** | Separate orders | Built-in split TP/SL |
| **Margin Management** | Fixed | Dynamic add/reduce margin |
| **Funding Fees** | None | Periodic funding rate payments |
| **Liquidation** | Margin call → square-off | Automatic liquidation with alerts |

### 3. Technical Differences

| Component | Stock Trading | Crypto Futures (Pi42) |
|-----------|--------------|----------------------|
| **Authentication** | OAuth2/TOTP/API Key | HMAC-SHA256 signature |
| **Symbol Format** | Exchange-specific | Unified (BTCUSDT) |
| **Master Contract** | Daily CSV download | Exchange info API |
| **WebSocket Auth** | Broker-specific | Listen key or signature |
| **Rate Limits** | Varies by broker | Strict per-endpoint limits |
| **Base URLs** | Single URL | Separate public/authenticated |
| **Decimal Precision** | 2 decimals (price) | Variable (0.001 BTC, 0.01 USDT) |

### 4. Data Structure Differences

**Stock Trading Position:**
```python
{
    "symbol": "SBIN",
    "exchange": "NSE",
    "product": "MIS",
    "quantity": 100,
    "average_price": 625.50
}
```

**Crypto Futures Position:**
```python
{
    "symbol": "BTCUSDT",
    "side": "LONG",
    "leverage": 10,
    "marginMode": "ISOLATED",
    "marginAsset": "USDT",
    "quantity": 0.5,
    "entryPrice": 50000,
    "markPrice": 51000,
    "liquidationPrice": 45000,
    "unrealizedPnl": 500,
    "margin": 2500,
    "fundingFee": -2.5
}
```

## Architectural Changes Required

### 1. Core OpenAlgo Changes

#### 1.1 Exchange Type System
- Add `broker_type` field: `"IN_stock"` vs `"CRYPTO_futures"`
- Conditional logic based on broker type throughout codebase
- Separate UI components for crypto vs stock

#### 1.2 Symbol Management
- Crypto symbols don't need exchange parameter (always Pi42)
- No expiry dates for perpetual futures
- Strike price not applicable
- Lot size replaced by minimum quantity

#### 1.3 Product/Margin System
- Replace product types (MIS/NRML/CNC) with margin modes (ISOLATED/CROSS)
- Add leverage configuration per order
- Add margin asset selection (INR/USDT)

#### 1.4 Order System
- Add STOP_MARKET and STOP_LIMIT order types
- Implement split TP/SL functionality
- Add margin add/reduce operations
- Handle funding fee tracking

#### 1.5 Position Management
- Track liquidation price
- Monitor unrealized PnL in real-time
- Handle funding fee deductions
- Implement margin call alerts

#### 1.6 Time Management
- Remove market hours restrictions for crypto
- 24/7 trading support
- No auto square-off at EOD

### 2. Database Schema Changes

#### 2.1 SymToken Table Extensions
```sql
ALTER TABLE symtoken ADD COLUMN broker_type VARCHAR(20);
ALTER TABLE symtoken ADD COLUMN min_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN max_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN price_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN quantity_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN margin_assets TEXT; -- JSON array
ALTER TABLE symtoken ADD COLUMN max_leverage INTEGER;
```

#### 2.2 New Tables for Crypto

**Funding Fees Table:**
```sql
CREATE TABLE funding_fees (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    symbol VARCHAR(50),
    funding_rate FLOAT,
    funding_fee FLOAT,
    timestamp DATETIME,
    position_size FLOAT
);
```

**Liquidation History:**
```sql
CREATE TABLE liquidations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    symbol VARCHAR(50),
    side VARCHAR(10),
    quantity FLOAT,
    liquidation_price FLOAT,
    loss FLOAT,
    timestamp DATETIME
);
```

**Margin Operations:**
```sql
CREATE TABLE margin_operations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    symbol VARCHAR(50),
    operation VARCHAR(10), -- ADD/REDUCE
    amount FLOAT,
    margin_asset VARCHAR(10),
    timestamp DATETIME
);
```

### 3. API Endpoint Changes

#### 3.1 New Endpoints Required

**Leverage Management:**
- `POST /api/v1/setleverage` - Set leverage for symbol
- `GET /api/v1/getleverage` - Get current leverage

**Margin Management:**
- `POST /api/v1/addmargin` - Add margin to position
- `POST /api/v1/reducemargin` - Reduce margin from position

**Split TP/SL:**
- `POST /api/v1/splittakeprofit` - Set multiple TP levels
- `POST /api/v1/splitstoploss` - Set multiple SL levels

**Funding:**
- `GET /api/v1/fundingrate` - Get current funding rate
- `GET /api/v1/fundinghistory` - Get funding fee history

**Liquidation:**
- `GET /api/v1/liquidationprice` - Calculate liquidation price
- `GET /api/v1/liquidationhistory` - Get liquidation history

#### 3.2 Modified Endpoints

**Place Order:**
```python
# Add new fields
{
    "symbol": "BTCUSDT",
    "action": "BUY",
    "quantity": 0.5,
    "pricetype": "LIMIT",
    "price": 50000,
    "leverage": 10,  # NEW
    "marginMode": "ISOLATED",  # NEW
    "marginAsset": "USDT",  # NEW
    "stopPrice": 49000  # NEW for STOP orders
}
```

**Positions:**
```python
# Return crypto-specific fields
{
    "symbol": "BTCUSDT",
    "side": "LONG",
    "quantity": 0.5,
    "entryPrice": 50000,
    "markPrice": 51000,
    "liquidationPrice": 45000,  # NEW
    "unrealizedPnl": 500,  # NEW
    "margin": 2500,  # NEW
    "leverage": 10,  # NEW
    "marginMode": "ISOLATED"  # NEW
}
```

### 4. Frontend Changes

#### 4.1 New UI Components

**Leverage Selector:**
- Slider/input for 1x-25x leverage
- Real-time liquidation price calculation
- Margin requirement display

**Margin Mode Toggle:**
- Switch between ISOLATED/CROSS
- Explanation tooltips

**Margin Asset Selector:**
- Dropdown for INR/USDT
- Balance display for each asset

**Position Card Enhancements:**
- Liquidation price indicator
- Unrealized PnL (real-time)
- Funding fee tracker
- Margin add/reduce buttons

**Split TP/SL Interface:**
- Multiple TP/SL level configuration
- Percentage-based or price-based
- Visual representation

#### 4.2 Modified Components

**Order Form:**
- Add leverage slider
- Add margin mode toggle
- Add margin asset selector
- Add stop price field for STOP orders

**Position Book:**
- Show liquidation price
- Show unrealized PnL
- Show funding fees
- Color-code by risk level

**Dashboard:**
- 24/7 market status (no market hours)
- Funding rate display
- Liquidation alerts

### 5. WebSocket Enhancements

#### 5.1 New WebSocket Events

**Position Updates:**
- Real-time mark price changes
- Unrealized PnL updates
- Liquidation price changes

**Funding Events:**
- Funding rate updates (every 8 hours)
- Funding fee deductions

**Risk Alerts:**
- Margin call warnings
- Liquidation warnings
- High funding rate alerts

#### 5.2 WebSocket Authentication

Pi42 uses two methods:
1. **Listen Key** - Create key, use in WebSocket URL
2. **Signature** - HMAC-SHA256 signature in connection

Implement both methods with fallback.

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
1. Add broker_type system to codebase
2. Extend database schema
3. Create Pi42 broker directory structure
4. Implement HMAC-SHA256 authentication
5. Create base API client with signature generation

### Phase 2: Basic Trading (Week 3-4)
1. Implement order placement (MARKET, LIMIT)
2. Implement order cancellation
3. Implement position fetching
4. Implement balance/wallet APIs
5. Basic master contract (exchange info)

### Phase 3: Advanced Features (Week 5-6)
1. Implement STOP orders
2. Implement leverage management
3. Implement margin add/reduce
4. Implement split TP/SL
5. Funding fee tracking

### Phase 4: Market Data (Week 7)
1. Implement quotes API
2. Implement depth API
3. Implement historical klines
4. Implement ticker data

### Phase 5: WebSocket Integration (Week 8-9)
1. Implement WebSocket authentication
2. Implement order update stream
3. Implement position update stream
4. Implement funding fee stream
5. Implement liquidation alerts

### Phase 6: Frontend (Week 10-11)
1. Create crypto-specific UI components
2. Implement leverage controls
3. Implement margin management UI
4. Implement split TP/SL UI
5. Real-time position updates

### Phase 7: Testing & Documentation (Week 12)
1. Integration testing
2. Load testing
3. Documentation
4. User guide for crypto trading

## Risk Considerations

### 1. Technical Risks
- **24/7 Operations**: Server must handle continuous trading
- **High Volatility**: Rapid price changes require fast execution
- **Liquidations**: Must handle automatic liquidations correctly
- **Funding Fees**: Accurate calculation and tracking critical

### 2. User Experience Risks
- **Complexity**: Crypto futures more complex than stocks
- **Leverage Risk**: Users may over-leverage
- **Liquidation Risk**: Users may not understand liquidation
- **Funding Costs**: Users may not expect funding fees

### 3. Mitigation Strategies
- Clear warnings about leverage and liquidation
- Educational tooltips and guides
- Risk calculators (liquidation price, funding cost)
- Conservative default settings (low leverage)
- Mandatory risk acknowledgment

## Testing Strategy

### 1. Unit Tests
- Signature generation
- Order transformations
- Position calculations
- Liquidation price calculations

### 2. Integration Tests
- Order placement flow
- Position management
- Margin operations
- WebSocket connections

### 3. Load Tests
- 24/7 continuous operation
- High-frequency order updates
- WebSocket stability
- Rate limit handling

### 4. User Acceptance Tests
- Complete trading workflow
- Leverage adjustment
- Margin management
- Split TP/SL functionality

## Documentation Requirements

### 1. Developer Documentation
- Pi42 API integration guide
- Crypto-specific architecture
- Database schema changes
- WebSocket implementation

### 2. User Documentation
- Crypto futures trading guide
- Leverage and margin explained
- Funding fees explained
- Risk management guide
- Liquidation prevention guide

### 3. API Documentation
- New endpoint specifications
- Modified endpoint changes
- WebSocket event documentation
- Error codes and handling

## Success Criteria

### 1. Functional Requirements
- ✅ Place/modify/cancel orders successfully
- ✅ Manage positions with leverage
- ✅ Add/reduce margin dynamically
- ✅ Set split TP/SL levels
- ✅ Track funding fees accurately
- ✅ Receive liquidation alerts
- ✅ Real-time WebSocket updates

### 2. Performance Requirements
- ✅ Order execution < 500ms
- ✅ WebSocket latency < 100ms
- ✅ 99.9% uptime (24/7)
- ✅ Handle 100+ concurrent users
- ✅ Rate limit compliance

### 3. User Experience Requirements
- ✅ Intuitive leverage controls
- ✅ Clear risk indicators
- ✅ Real-time PnL updates
- ✅ Comprehensive error messages
- ✅ Mobile-responsive design

## Next Steps

1. Review and approve this master plan
2. Set up Pi42 test account
3. Create detailed technical specifications for each phase
4. Begin Phase 1 implementation
5. Establish testing environment

---

**Note**: This is a living document and will be updated as implementation progresses and new requirements are discovered.
