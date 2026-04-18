# Broker Integration Guide - Based on Kotak Implementation

This guide explains how to add new broker integrations to OpenAlgo, using the Kotak broker implementation as a reference example.

## Overview

OpenAlgo uses a standardized broker integration architecture where each broker is implemented as a self-contained module under the `broker/` directory. The Kotak broker (`broker/kotak/`) serves as an excellent reference implementation demonstrating all required components.

## Directory Structure

Each broker integration follows this standardized structure:

```
broker/your_broker_name/
├── api/
│   ├── __init__.py
│   ├── auth_api.py           # Authentication and session management
│   ├── order_api.py          # Order placement, modification, cancellation
│   ├── data.py               # Market data, quotes, historical data
│   ├── funds.py              # Account balance and margin
│   └── margin_api.py         # Margin calculation (optional)
├── database/
│   └── master_contract_db.py # Symbol master contract management
├── mapping/
│   ├── order_data.py         # Transform broker responses to OpenAlgo format
│   ├── transform_data.py     # Transform OpenAlgo requests to broker format
│   └── margin_data.py        # Margin data transformations (optional)
├── streaming/                # WebSocket streaming (optional)
│   └── broker_adapter.py     # WebSocket adapter for live data
└── plugin.json               # Broker configuration metadata
```

## Step-by-Step Implementation Guide

### 1. Create Plugin Configuration (`plugin.json`)

Define broker metadata and capabilities:

```json
{
    "Plugin Name": "brokername",
    "Plugin URI": "https://openalgo.in",
    "Description": "BrokerName OpenAlgo Plugin",
    "Version": "1.0",
    "Author": "Your Name",
    "Author URI": "https://openalgo.in",
    "supported_exchanges": ["NSE", "BSE", "NFO", "BFO", "CDS", "MCX", "NSE_INDEX", "BSE_INDEX"],
    "broker_type": "IN_stock",
    "leverage_config": false
}
```

**Key Fields:**
- `supported_exchanges`: List of exchanges your broker supports
- `broker_type`: Usually "IN_stock" for Indian brokers
- `leverage_config`: Set to `true` if broker supports custom leverage settings

### 2. Implement Authentication (`api/auth_api.py`)

The authentication module handles broker login and token management.

**Kotak Example - Two-Step Authentication:**

```python
def authenticate_broker(mobile_number, totp, mpin):
    """
    Authenticate with broker using credentials.
    
    Returns:
        Tuple of (auth_string, error_message)
        auth_string format: "token:::sid:::base_url:::access_token"
    """
    # Step 1: Login with TOTP
    # Step 2: Validate with MPIN
    # Return auth string with all required tokens
```

**Key Points:**
- Authentication function receives credentials from user
- Must return auth token string that will be stored in database
- Auth token format should contain all information needed for API calls
- Use `:::` as delimiter to separate multiple token components
- Handle errors gracefully and return descriptive error messages

**Common Authentication Patterns:**
- **OAuth2 Flow**: Redirect user to broker login page, receive callback with token
- **API Key + Secret**: Direct authentication with API credentials
- **TOTP/MPIN**: Two-factor authentication (like Kotak)
- **Session-based**: Login returns session token for subsequent API calls

### 3. Implement Order Management (`api/order_api.py`)

This is the core module for trading operations.

**Required Functions:**

#### 3.1 Place Order
```python
def place_order_api(data, auth_token):
    """
    Place a new order with the broker.
    
    Args:
        data: Order data in OpenAlgo format
        auth_token: Authentication token
        
    Returns:
        Tuple of (response, response_data, orderid)
    """
    # 1. Extract auth components from auth_token
    # 2. Get broker symbol using get_token(data["symbol"], data["exchange"])
    # 3. Transform data to broker format using transform_data()
    # 4. Make API request to broker
    # 5. Return response, response_data, orderid
```

#### 3.2 Modify Order
```python
def modify_order(data, auth_token):
    """
    Modify an existing order.
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    # Similar to place_order but includes orderid
```

#### 3.3 Cancel Order
```python
def cancel_order(orderid, auth_token):
    """
    Cancel an order by orderid.
    
    Returns:
        Tuple of (response_dict, status_code)
    """
```

#### 3.4 Get Order Book
```python
def get_order_book(auth_token):
    """
    Fetch all orders for the day.
    
    Returns:
        Dictionary with order data
    """
```

#### 3.5 Get Trade Book
```python
def get_trade_book(auth_token):
    """
    Fetch all executed trades.
    """
```

#### 3.6 Get Positions
```python
def get_positions(auth_token):
    """
    Fetch current open positions.
    """
```

#### 3.7 Get Holdings
```python
def get_holdings(auth_token):
    """
    Fetch demat holdings.
    """
```

#### 3.8 Smart Order (Advanced)
```python
def place_smartorder_api(data, auth_token):
    """
    Place smart order that adjusts position to target size.
    
    Smart orders:
    - Check current position
    - Calculate required action (BUY/SELL) and quantity
    - Place order to reach target position_size
    """
    # 1. Get current position using get_open_position()
    # 2. Calculate difference between target and current
    # 3. Place order to adjust position
```

**Kotak Smart Order Features:**
- Per-symbol locking to serialize smart orders
- Position cache with 1-second TTL
- Automatic position refresh after order placement

#### 3.9 Close All Positions
```python
def close_all_positions(current_api_key, auth_token):
    """
    Square off all open positions.
    """
    # 1. Get all positions
    # 2. For each position with net_qty != 0:
    #    - Determine action (SELL if long, BUY if short)
    #    - Place market order to close
```

#### 3.10 Cancel All Orders
```python
def cancel_all_orders_api(data, auth_token):
    """
    Cancel all pending orders.
    
    Returns:
        Tuple of (canceled_orders, failed_cancellations)
    """
```

**Important Implementation Notes:**

1. **Use httpx Connection Pooling:**
```python
from utils.httpx_client import get_httpx_client
client = get_httpx_client()
response = client.post(url, headers=headers, content=payload)
```

2. **Token Database Functions:**
```python
from database.token_db import get_token, get_br_symbol, get_symbol

# Get broker token for symbol
token = get_token(symbol, exchange)

# Get broker symbol format
br_symbol = get_br_symbol(symbol, exchange)

# Get OpenAlgo symbol from broker token
oa_symbol = get_symbol(token, exchange)
```

3. **Error Handling:**
- Always wrap API calls in try-except blocks
- Return consistent error format: `{"status": "error", "message": "..."}`
- Log errors with context using the logger

### 4. Implement Market Data (`api/data.py`)

Market data module provides quotes, depth, and historical data.

**Kotak Example Structure:**

```python
class BrokerData:
    def __init__(self, auth_token):
        """Initialize with auth token and parse components."""
        self.session_token, self.session_sid, self.base_url, self.access_token = auth_token.split(":::")
        
    def get_quotes(self, symbol, exchange):
        """
        Get real-time quotes for a symbol.
        
        Returns:
            {
                "bid": float,
                "ask": float,
                "open": float,
                "high": float,
                "low": float,
                "ltp": float,
                "prev_close": float,
                "volume": float,
                "oi": int
            }
        """
        
    def get_depth(self, symbol, exchange):
        """
        Get market depth (Level 5 order book).
        
        Returns:
            {
                "bids": [{"price": float, "quantity": int}, ...],  # 5 levels
                "asks": [{"price": float, "quantity": int}, ...],  # 5 levels
                "totalbuyqty": int,
                "totalsellqty": int
            }
        """
        
    def get_multiquotes(self, symbols):
        """
        Get quotes for multiple symbols in batch.
        
        Args:
            symbols: [{"symbol": "SBIN", "exchange": "NSE"}, ...]
            
        Returns:
            [{"symbol": "SBIN", "exchange": "NSE", "data": {...}}, ...]
        """
        
    def get_history(self, symbol, exchange, interval, start_date, end_date):
        """
        Get historical OHLC data.
        
        Returns:
            pandas.DataFrame with columns: timestamp, open, high, low, close, volume
        """
        
    def get_supported_intervals(self):
        """
        Return supported timeframe intervals.
        
        Returns:
            {
                "seconds": [],
                "minutes": [1, 3, 5, 15, 30],
                "hours": [1],
                "days": [1],
                "weeks": [1],
                "months": [1]
            }
        """
```

**Key Implementation Points:**

1. **Symbol Resolution:**
   - Use `get_token()` to get broker's internal symbol identifier
   - Use `get_brexchange()` to get broker's exchange format
   - Handle index symbols separately (they may use different format)

2. **Exchange Mapping:**
```python
def _get_kotak_exchange(self, exchange):
    """Map OpenAlgo exchange to broker exchange format."""
    exchange_map = {
        "NSE": "nse_cm",
        "BSE": "bse_cm",
        "NFO": "nse_fo",
        "BFO": "bse_fo",
        "CDS": "cde_fo",
        "MCX": "mcx_fo",
    }
    return exchange_map.get(exchange)
```

3. **Batch Requests:**
   - Implement batching for multiquotes to avoid rate limits
   - Add rate limiting delays between batches
   - Handle partial failures gracefully

4. **Default Values:**
   - Always return default structure even on errors
   - Prevents downstream errors in OpenAlgo

### 5. Implement Funds API (`api/funds.py`)

Fetch account balance and margin information.

```python
def get_margin_data(auth_token):
    """
    Get account margin and balance information.
    
    Returns:
        Dictionary with margin data in broker format
    """
```

### 6. Implement Data Transformations (`mapping/transform_data.py`)

Transform data between OpenAlgo format and broker format.

**Key Functions:**

#### 6.1 Transform Order Data (OpenAlgo → Broker)
```python
def transform_data(data, token, auth_token=None):
    """
    Transform OpenAlgo order request to broker format.
    
    Args:
        data: OpenAlgo order data
        token: Broker instrument token
        auth_token: Auth token (for fetching quotes if needed)
        
    Returns:
        Dictionary in broker's API format
    """
    # 1. Get broker symbol
    symbol = get_br_symbol(data["symbol"], data["exchange"])
    
    # 2. Map order type
    order_type = map_order_type(data["pricetype"])
    
    # 3. Map exchange
    exchange = reverse_map_exchange(data["exchange"])
    
    # 4. Build broker request format
    transformed = {
        "symbol": symbol,
        "exchange": exchange,
        "action": data["action"],
        "quantity": data["quantity"],
        "price": data.get("price", "0"),
        "order_type": order_type,
        "product": data.get("product", "MIS"),
        # ... other broker-specific fields
    }
    
    return transformed
```

#### 6.2 Market Price Protection (MPP)

Kotak implements MPP to convert MARKET orders to LIMIT orders with protective pricing:

```python
# For MARKET orders:
# 1. Fetch current LTP using BrokerData.get_quotes()
# 2. Calculate protected price based on instrument type:
#    - EQ/FUT: Price < 100: 2%, 100-500: 1%, > 500: 0.5%
#    - OPT: Price < 10: 5%, 10-100: 3%, 100-500: 2%, > 500: 1%
# 3. Convert MARKET to LIMIT with protected price
```

Use centralized MPP utility:
```python
from utils.mpp_slab import calculate_protected_price, get_instrument_type_from_symbol

protected_price = calculate_protected_price(
    price=ltp,
    action=action,
    symbol=symbol,
    instrument_type=instrument_type,
    tick_size=tick_size
)
```

#### 6.3 Exchange Mapping
```python
def map_exchange(brexchange):
    """Map broker exchange to OpenAlgo exchange."""
    exchange_mapping = {
        "nse_cm": "NSE",
        "bse_cm": "BSE",
        "nse_fo": "NFO",
        # ...
    }
    return exchange_mapping.get(brexchange)

def reverse_map_exchange(exchange):
    """Map OpenAlgo exchange to broker exchange."""
    # Reverse of above
```

#### 6.4 Product Type Mapping
```python
def map_product_type(product):
    """Map OpenAlgo product to broker product."""
    product_mapping = {
        "CNC": "CNC",      # Delivery
        "NRML": "NRML",    # Normal (F&O)
        "MIS": "MIS",      # Intraday
    }
    return product_mapping.get(product)
```

#### 6.5 Order Type Mapping
```python
def map_order_type(pricetype):
    """Map OpenAlgo pricetype to broker order type."""
    order_type_mapping = {
        "MARKET": "MKT",
        "LIMIT": "L",
        "SL": "SL",
        "SL-M": "SL-M"
    }
    return order_type_mapping.get(pricetype, "MARKET")
```

### 7. Implement Response Transformations (`mapping/order_data.py`)

Transform broker responses to OpenAlgo format for display.

**Key Functions:**

#### 7.1 Map Order Data
```python
def map_order_data(order_data):
    """
    Transform broker order response to OpenAlgo format.
    
    - Replace broker symbols with OpenAlgo symbols
    - Map exchange codes
    - Normalize field names
    """
    if order_data.get("data"):
        for order in order_data["data"]:
            # Get OpenAlgo symbol from broker token
            symboltoken = order["token_field"]
            exchange = map_exchange(order["exchange_field"])
            symbol = get_symbol(symboltoken, exchange)
            
            if symbol:
                order["symbol"] = symbol
            order["exchange"] = exchange
    
    return order_data
```

#### 7.2 Transform Order Data
```python
def transform_order_data(orders):
    """
    Transform order data to standardized format for UI.
    
    Returns:
        [
            {
                "symbol": str,
                "exchange": str,
                "action": "BUY" | "SELL",
                "quantity": int,
                "price": float,
                "trigger_price": float,
                "pricetype": "MARKET" | "LIMIT" | "SL" | "SL-M",
                "product": str,
                "orderid": str,
                "order_status": str,
                "timestamp": str
            },
            ...
        ]
    """
```

#### 7.3 Calculate Statistics
```python
def calculate_order_statistics(order_data):
    """
    Calculate order statistics for dashboard.
    
    Returns:
        {
            "total_buy_orders": int,
            "total_sell_orders": int,
            "total_completed_orders": int,
            "total_open_orders": int,
            "total_rejected_orders": int
        }
    """
```

Similar functions for:
- `map_trade_data()` - Transform trade book
- `transform_tradebook_data()` - Standardize trade book
- `map_position_data()` - Transform positions
- `transform_positions_data()` - Standardize positions
- `map_portfolio_data()` - Transform holdings
- `transform_holdings_data()` - Standardize holdings
- `calculate_portfolio_statistics()` - Portfolio stats

### 8. Implement Master Contract Database (`database/master_contract_db.py`)

Master contract database stores symbol mappings between OpenAlgo and broker formats.

**Database Schema:**

```python
class SymToken(Base):
    __tablename__ = "symtoken"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)      # OpenAlgo symbol
    brsymbol = Column(String, nullable=False, index=True)    # Broker symbol
    name = Column(String)                                     # Instrument name
    exchange = Column(String, index=True)                     # OpenAlgo exchange
    brexchange = Column(String, index=True)                   # Broker exchange
    token = Column(String, index=True)                        # Broker token/ID
    expiry = Column(String)                                   # Expiry date (F&O)
    strike = Column(Float)                                    # Strike price (options)
    lotsize = Column(Integer)                                 # Lot size
    instrumenttype = Column(String)                           # EQ/FUT/CE/PE
    tick_size = Column(Float)                                 # Minimum price movement
    
    __table_args__ = (Index("idx_symbol_exchange", "symbol", "exchange"),)
```

**Required Functions:**

#### 8.1 Download Master Contract
```python
def download_csv_broker_data(output_path):
    """
    Download master contract files from broker.
    
    Returns:
        List of downloaded file paths
    """
    # 1. Get master contract URLs from broker API
    # 2. Download CSV/JSON files
    # 3. Save to output_path
    # 4. Return list of file paths
```

#### 8.2 Process Master Contract Files
```python
def process_broker_nse_csv(path):
    """
    Process NSE equity master contract.
    
    Returns:
        pandas.DataFrame with standardized columns
    """
    # 1. Read CSV file
    # 2. Map broker columns to OpenAlgo schema
    # 3. Add exchange information
    # 4. Return DataFrame
```

Similar functions for each exchange:
- `process_broker_nfo_csv()` - NSE F&O
- `process_broker_bse_csv()` - BSE equity
- `process_broker_bfo_csv()` - BSE F&O
- `process_broker_cds_csv()` - Currency derivatives
- `process_broker_mcx_csv()` - Commodity

#### 8.3 Master Contract Refresh
```python
def master_contract_download():
    """
    Main function to refresh master contract database.
    
    Steps:
    1. Download CSV files from broker
    2. Process each exchange file
    3. Combine into single DataFrame
    4. Bulk insert into database
    5. Emit progress via SocketIO
    """
    try:
        # Download files
        socketio.emit('master_contract_download', {'status': 'downloading'})
        files = download_csv_broker_data(path)
        
        # Process files
        socketio.emit('master_contract_download', {'status': 'processing'})
        dfs = []
        dfs.append(process_broker_nse_csv(path))
        dfs.append(process_broker_nfo_csv(path))
        # ... other exchanges
        
        # Combine and insert
        combined_df = pd.concat(dfs, ignore_index=True)
        delete_symtoken_table()  # Clear old data
        copy_from_dataframe(combined_df)
        
        socketio.emit('master_contract_download', {'status': 'complete'})
        return {"status": "success"}
    except Exception as e:
        socketio.emit('master_contract_download', {'status': 'error', 'message': str(e)})
        return {"status": "error", "message": str(e)}
```

**Column Mapping Example (Kotak):**

```python
# Broker CSV columns → OpenAlgo schema
filtereddataframe["token"] = df["pSymbol"]           # Broker's symbol ID
filtereddataframe["symbol"] = df["pTrdSymbol"]       # OpenAlgo trading symbol
filtereddataframe["brsymbol"] = df["pSymbol"]        # Broker symbol
filtereddataframe["name"] = df["pDesc"]              # Instrument name
filtereddataframe["exchange"] = "NSE"                # OpenAlgo exchange
filtereddataframe["brexchange"] = "nse_cm"           # Broker exchange
filtereddataframe["lotsize"] = df["pPrcQty"]         # Lot size
filtereddataframe["tick_size"] = df["pTickSize"]     # Tick size
```

### 9. Implement WebSocket Streaming (Optional)

If broker supports WebSocket for real-time data:

```python
# streaming/broker_adapter.py

class BrokerWebSocketAdapter:
    """
    WebSocket adapter for real-time market data.
    
    Integrates with OpenAlgo's unified WebSocket proxy server.
    """
    
    def __init__(self, auth_token):
        """Initialize with auth token."""
        
    def connect(self):
        """Establish WebSocket connection to broker."""
        
    def subscribe(self, symbols, mode="LTP"):
        """
        Subscribe to symbols.
        
        Args:
            symbols: List of (symbol, exchange) tuples
            mode: "LTP" | "QUOTE" | "DEPTH"
        """
        
    def unsubscribe(self, symbols):
        """Unsubscribe from symbols."""
        
    def on_message(self, message):
        """
        Handle incoming WebSocket message.
        
        Transform broker format to OpenAlgo format and publish to ZMQ.
        """
        
    def disconnect(self):
        """Close WebSocket connection."""
```

## Testing Your Integration

### 1. Environment Configuration

Add broker to `.env`:

```bash
# Add broker to valid brokers list
VALID_BROKERS=zerodha,kotak,yourbrokername

# Broker API credentials
BROKER_API_KEY=your_api_key
BROKER_API_SECRET=your_api_secret
```

### 2. Test Authentication

```python
# Test login flow
from broker.yourbrokername.api.auth_api import authenticate_broker

auth_token, error = authenticate_broker(credentials)
if error:
    print(f"Auth failed: {error}")
else:
    print(f"Auth successful: {auth_token}")
```

### 3. Test Master Contract Download

```bash
# Via UI: Settings → Master Contract → Download
# Or via API: POST /api/v1/downloadmastercontract
```

### 4. Test Order Placement

Use Swagger UI at `http://127.0.0.1:5000/api/docs`:

1. Authenticate via `/api/v1/auth`
2. Test `/api/v1/placeorder` with sample data
3. Verify order appears in broker's order book

### 5. Test Market Data

```python
from broker.yourbrokername.api.data import BrokerData

broker_data = BrokerData(auth_token)
quotes = broker_data.get_quotes("SBIN", "NSE")
print(quotes)
```

### 6. Test All Endpoints

Test each API endpoint via Swagger:
- `/api/v1/placeorder`
- `/api/v1/modifyorder`
- `/api/v1/cancelorder`
- `/api/v1/orderbook`
- `/api/v1/tradebook`
- `/api/v1/positionbook`
- `/api/v1/holdings`
- `/api/v1/quotes`
- `/api/v1/depth`
- `/api/v1/funds`

## Common Patterns and Best Practices

### 1. Error Handling

```python
try:
    response = client.post(url, headers=headers, content=payload)
    response_data = json.loads(response.text)
    
    if response_data.get("status") == "success":
        return {"status": "success", "data": response_data}, 200
    else:
        return {"status": "error", "message": response_data.get("message")}, 400
        
except httpx.HTTPError as e:
    logger.error(f"HTTP error: {e}")
    return {"status": "error", "message": str(e)}, 500
except Exception as e:
    logger.error(f"Error: {e}")
    return {"status": "error", "message": str(e)}, 500
```

### 2. Logging

```python
from utils.logging import get_logger

logger = get_logger(__name__)

# Log important events
logger.info(f"Placing order: {symbol} {action} {quantity}")
logger.debug(f"Request payload: {payload}")
logger.error(f"Order placement failed: {error}")
```

### 3. Connection Pooling

Always use the shared httpx client:

```python
from utils.httpx_client import get_httpx_client

client = get_httpx_client()
response = client.post(url, headers=headers, content=payload)
```

### 4. Token Database Queries

```python
from database.token_db import get_token, get_br_symbol, get_symbol, get_brexchange

# Get broker token for OpenAlgo symbol
token = get_token("SBIN", "NSE")

# Get broker symbol format
br_symbol = get_br_symbol("SBIN", "NSE")

# Get broker exchange format
br_exchange = get_brexchange("SBIN", "NSE")

# Reverse: Get OpenAlgo symbol from broker token
oa_symbol = get_symbol(token, "NSE")
```

### 5. Response Format Consistency

Always return consistent response format:

```python
# Success
{
    "status": "success",
    "message": "Order placed successfully",
    "data": {
        "orderid": "123456"
    }
}

# Error
{
    "status": "error",
    "message": "Insufficient funds"
}
```

## Broker-Specific Considerations

### Authentication Methods

**OAuth2 (Zerodha, Upstox):**
- Redirect user to broker login page
- Receive callback with authorization code
- Exchange code for access token

**API Key + Secret (Dhan, Fyers):**
- Direct authentication with credentials
- No redirect flow needed

**TOTP/MPIN (Kotak):**
- Two-step authentication
- TOTP from authenticator app
- MPIN for trading access

### API Rate Limits

Implement rate limiting if broker has restrictions:

```python
import time

RATE_LIMIT_DELAY = 0.2  # 5 requests/second

for batch in batches:
    process_batch(batch)
    time.sleep(RATE_LIMIT_DELAY)
```

### Symbol Formats

Different brokers use different symbol formats:

**Zerodha:** `SBIN`, `NIFTY24JAN24000CE`
**Kotak:** `SBIN-EQ`, `NIFTY 24 JAN 24000 CE`
**Dhan:** `1333`, `52175` (numeric tokens)

Master contract database handles these conversions.

### Exchange Codes

Map broker exchange codes to OpenAlgo standard:

```python
# Broker → OpenAlgo
"nse_cm" → "NSE"
"nse_fo" → "NFO"
"bse_cm" → "BSE"
"bse_fo" → "BFO"
"cde_fo" → "CDS"
"mcx_fo" → "MCX"
```

## Troubleshooting

### Master Contract Download Fails

1. Check broker API credentials in `.env`
2. Verify broker API is accessible
3. Check master contract URL format
4. Review logs for specific error

### Orders Not Placing

1. Verify authentication token is valid
2. Check symbol exists in master contract database
3. Verify exchange mapping is correct
4. Check broker API response for error details

### Quotes Not Working

1. Verify symbol format matches broker requirements
2. Check if broker requires special handling for indices
3. Verify exchange mapping
4. Check rate limits

### WebSocket Connection Issues

1. Verify WebSocket URL and authentication
2. Check if broker requires special headers
3. Verify message format transformation
4. Check ZMQ publisher is running

## Reference Implementations

### Simple Broker (API Key Auth)
- **Dhan**: Simple API key authentication, numeric tokens
- **Fyers**: API key + secret, straightforward REST API

### Complex Broker (OAuth2)
- **Zerodha**: OAuth2 flow, comprehensive API, WebSocket support
- **Upstox**: OAuth2, modern REST API

### Advanced Features (TOTP/MPIN)
- **Kotak**: Two-step auth, MPP implementation, position caching

## Submission Checklist

Before submitting your broker integration:

- [ ] All required API functions implemented
- [ ] Master contract download working for all exchanges
- [ ] Order placement, modification, cancellation tested
- [ ] Market data (quotes, depth) working
- [ ] Positions, holdings, funds API working
- [ ] Error handling implemented throughout
- [ ] Logging added for debugging
- [ ] Exchange and product type mappings correct
- [ ] Symbol transformations working both ways
- [ ] Response transformations to OpenAlgo format
- [ ] Plugin.json configured correctly
- [ ] Tested with real broker account
- [ ] Documentation updated (if needed)

## Getting Help

- **Discord**: [OpenAlgo Community](https://discord.com/invite/UPh7QPsNhP)
- **Documentation**: [docs.openalgo.in](https://docs.openalgo.in)
- **GitHub Issues**: [Report issues](https://github.com/marketcalls/openalgo/issues)
- **Reference Code**: Study `broker/kotak/` and `broker/zerodha/` implementations

## Contributing

When submitting a new broker integration:

1. Create a feature branch: `git checkout -b feature/add-brokername`
2. Implement broker following this guide
3. Test thoroughly with real broker account
4. Submit pull request with:
   - Clear description of broker
   - Testing evidence (screenshots)
   - Any special configuration notes
5. One broker per pull request (see CONTRIBUTING.md)

---

**Built by traders, for traders — making algo trading accessible to everyone.**
