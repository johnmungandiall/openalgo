# Pi42 Market Data Implementation Plan

## Overview

Pi42 provides comprehensive market data APIs for crypto futures trading, including real-time quotes, market depth, historical klines, and ticker data. This document details the market data implementation.

## Market Data Endpoints

### 1. Available Endpoints

| Endpoint | Type | Description |
|----------|------|-------------|
| `/v1/market/ticker24Hr/:contractPair` | Public | 24-hour ticker statistics |
| `/v1/market/depth/:contractPair` | Public | Order book depth (bids/asks) |
| `/v1/market/aggTrade/:contractPair` | Public | Aggregated recent trades |
| `/v1/market/klines` | Public | Historical candlestick data |
| `/v1/exchange/exchangeInfo` | Public | Contract specifications |

### 2. Key Differences from Stock Market Data

| Feature | Stock Market | Crypto (Pi42) |
|---------|-------------|---------------|
| **Trading Hours** | 9:15 AM - 3:30 PM | 24/7/365 |
| **Price Types** | LTP only | LTP + Mark Price + Index Price |
| **Funding** | None | Funding rate every 8 hours |
| **Intervals** | 1m, 5m, 15m, 1h, 1d | 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w |
| **Precision** | 2 decimals | Variable (BTC: 8, USDT: 2) |
| **Open Interest** | Not real-time | Real-time OI tracking |

## Implementation: `broker/pi42/api/data.py`

```python
"""
Pi42 Market Data API

Handles real-time quotes, market depth, historical data, and ticker information
for crypto futures trading.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from broker.pi42.api.auth_api import create_auth_instance
from database.token_db import get_token
from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)


class BrokerData:
    """Pi42 market data handler."""
    
    def __init__(self, auth_token: str):
        """
        Initialize Pi42 market data handler.
        
        Args:
            auth_token: Authentication token (not required for public endpoints)
        """
        self.auth_token = auth_token
        self.base_url = "https://api.pi42.com"  # Public API base URL
        self.auth_base_url = "https://fapi.pi42.com"  # Authenticated API base URL
        
        # Timeframe mapping
        self.timeframe_map = {
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "2h": "2h",
            "4h": "4h",
            "6h": "6h",
            "12h": "12h",
            "1d": "1d",
            "1w": "1w"
        }
        
        logger.info("Pi42 BrokerData initialized")
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Pi42 format.
        
        Args:
            symbol: Symbol in OpenAlgo format (e.g., "BTCUSDT")
            
        Returns:
            Symbol in Pi42 format (e.g., "BTCUSDT")
        """
        # Pi42 uses standard format: BTCUSDT, ETHUSDT, etc.
        # No exchange parameter needed
        return symbol.upper()
    
    def get_quotes(self, symbol: str, exchange: str = None) -> dict:
        """
        Get real-time quotes for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            exchange: Not used for crypto (kept for compatibility)
            
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
                "oi": int,
                "mark_price": float,  # NEW: Mark price for margin calculation
                "index_price": float,  # NEW: Index price
                "funding_rate": float  # NEW: Current funding rate
            }
        """
        try:
            symbol = self._normalize_symbol(symbol)
            logger.info(f"Fetching quotes for {symbol}")
            
            client = get_httpx_client()
            
            # Get 24hr ticker data
            url = f"{self.base_url}/v1/market/ticker24Hr/{symbol}"
            response = client.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch quotes: {response.status_code}")
                return self._get_default_quote()
            
            data = response.json()
            
            if not data.get("success"):
                logger.error(f"Quote API error: {data.get('message')}")
                return self._get_default_quote()
            
            ticker = data.get("data", {})
            
            # Parse Pi42 ticker format
            quotes = {
                "bid": float(ticker.get("bidPrice", 0)),
                "ask": float(ticker.get("askPrice", 0)),
                "open": float(ticker.get("openPrice", 0)),
                "high": float(ticker.get("highPrice", 0)),
                "low": float(ticker.get("lowPrice", 0)),
                "ltp": float(ticker.get("lastPrice", 0)),
                "prev_close": float(ticker.get("prevClosePrice", 0)),
                "volume": float(ticker.get("volume", 0)),
                "oi": int(ticker.get("openInterest", 0)),
                "mark_price": float(ticker.get("markPrice", 0)),
                "index_price": float(ticker.get("indexPrice", 0)),
                "funding_rate": float(ticker.get("fundingRate", 0))
            }
            
            logger.debug(f"Quotes for {symbol}: LTP={quotes['ltp']}, Mark={quotes['mark_price']}")
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error fetching quotes: {str(e)}")
            return self._get_default_quote()
    
    def get_depth(self, symbol: str, exchange: str = None, limit: int = 20) -> dict:
        """
        Get market depth (order book).
        
        Args:
            symbol: Trading symbol
            exchange: Not used for crypto
            limit: Number of levels (default 20, max 100)
            
        Returns:
            {
                "bids": [{"price": float, "quantity": float}, ...],
                "asks": [{"price": float, "quantity": float}, ...],
                "totalbuyqty": float,
                "totalsellqty": float
            }
        """
        try:
            symbol = self._normalize_symbol(symbol)
            logger.info(f"Fetching depth for {symbol} (limit: {limit})")
            
            client = get_httpx_client()
            
            # Get order book depth
            url = f"{self.base_url}/v1/market/depth/{symbol}?limit={limit}"
            response = client.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch depth: {response.status_code}")
                return self._get_default_depth()
            
            data = response.json()
            
            if not data.get("success"):
                logger.error(f"Depth API error: {data.get('message')}")
                return self._get_default_depth()
            
            depth_data = data.get("data", {})
            
            # Parse bids and asks
            bids = []
            for bid in depth_data.get("bids", [])[:5]:  # Top 5 levels
                bids.append({
                    "price": float(bid[0]),
                    "quantity": float(bid[1])
                })
            
            asks = []
            for ask in depth_data.get("asks", [])[:5]:  # Top 5 levels
                asks.append({
                    "price": float(ask[0]),
                    "quantity": float(ask[1])
                })
            
            # Ensure 5 levels
            while len(bids) < 5:
                bids.append({"price": 0, "quantity": 0})
            while len(asks) < 5:
                asks.append({"price": 0, "quantity": 0})
            
            # Calculate totals
            total_buy_qty = sum(bid["quantity"] for bid in bids if bid["quantity"] > 0)
            total_sell_qty = sum(ask["quantity"] for ask in asks if ask["quantity"] > 0)
            
            return {
                "bids": bids,
                "asks": asks,
                "totalbuyqty": total_buy_qty,
                "totalsellqty": total_sell_qty
            }
            
        except Exception as e:
            logger.error(f"Error fetching depth: {str(e)}")
            return self._get_default_depth()
    
    def get_multiquotes(self, symbols: List[dict]) -> List[dict]:
        """
        Get quotes for multiple symbols.
        
        Args:
            symbols: List of dicts with 'symbol' and 'exchange' keys
                     [{"symbol": "BTCUSDT", "exchange": "PI42"}, ...]
                     
        Returns:
            List of quote data for each symbol
            [{"symbol": "BTCUSDT", "exchange": "PI42", "data": {...}}, ...]
        """
        try:
            logger.info(f"Fetching multiquotes for {len(symbols)} symbols")
            
            results = []
            
            # Pi42 doesn't have batch quotes endpoint, fetch individually
            for item in symbols:
                symbol = item["symbol"]
                exchange = item.get("exchange", "PI42")
                
                try:
                    quote_data = self.get_quotes(symbol)
                    
                    results.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "data": quote_data
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch quote for {symbol}: {str(e)}")
                    results.append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "error": str(e)
                    })
            
            logger.info(f"Fetched quotes for {len(results)} symbols")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching multiquotes: {str(e)}")
            return []
    
    def get_history(self, symbol: str, exchange: str, interval: str, 
                    start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get historical candlestick data.
        
        Args:
            symbol: Trading symbol
            exchange: Not used for crypto
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            symbol = self._normalize_symbol(symbol)
            logger.info(f"Fetching history for {symbol} ({interval})")
            
            # Map interval to Pi42 format
            pi42_interval = self.timeframe_map.get(interval, "1h")
            
            # Convert dates to timestamps
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
            
            client = get_httpx_client()
            
            # Build request payload
            payload = {
                "symbol": symbol,
                "interval": pi42_interval,
                "priceType": "LAST_PRICE",  # or MARK_PRICE
                "startTime": start_ts,
                "endTime": end_ts,
                "limit": 1000  # Max limit
            }
            
            # Make API request
            response = client.post(
                f"{self.base_url}/v1/market/klines",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch history: {response.status_code}")
                return self._get_empty_dataframe()
            
            data = response.json()
            
            if not data.get("success"):
                logger.error(f"History API error: {data.get('message')}")
                return self._get_empty_dataframe()
            
            klines = data.get("data", [])
            
            if not klines:
                logger.warning(f"No historical data for {symbol}")
                return self._get_empty_dataframe()
            
            # Parse klines data
            # Format: [timestamp, open, high, low, close, volume, ...]
            df_data = []
            for kline in klines:
                df_data.append({
                    "timestamp": datetime.fromtimestamp(kline[0] / 1000),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5])
                })
            
            df = pd.DataFrame(df_data)
            
            logger.info(f"Fetched {len(df)} candles for {symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching history: {str(e)}")
            return self._get_empty_dataframe()
    
    def get_supported_intervals(self) -> dict:
        """
        Get supported timeframe intervals.
        
        Returns:
            {
                "seconds": [],
                "minutes": [1, 3, 5, 15, 30],
                "hours": [1, 2, 4, 6, 12],
                "days": [1],
                "weeks": [1],
                "months": []
            }
        """
        return {
            "seconds": [],
            "minutes": [1, 3, 5, 15, 30],
            "hours": [1, 2, 4, 6, 12],
            "days": [1],
            "weeks": [1],
            "months": []
        }
    
    def get_funding_rate(self, symbol: str) -> dict:
        """
        Get current funding rate for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            {
                "symbol": str,
                "funding_rate": float,
                "next_funding_time": int (timestamp),
                "mark_price": float,
                "index_price": float
            }
        """
        try:
            symbol = self._normalize_symbol(symbol)
            logger.info(f"Fetching funding rate for {symbol}")
            
            # Funding rate is included in ticker data
            quotes = self.get_quotes(symbol)
            
            return {
                "symbol": symbol,
                "funding_rate": quotes.get("funding_rate", 0),
                "mark_price": quotes.get("mark_price", 0),
                "index_price": quotes.get("index_price", 0)
            }
            
        except Exception as e:
            logger.error(f"Error fetching funding rate: {str(e)}")
            return {
                "symbol": symbol,
                "funding_rate": 0,
                "mark_price": 0,
                "index_price": 0
            }
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[dict]:
        """
        Get recent aggregated trades.
        
        Args:
            symbol: Trading symbol
            limit: Number of trades to fetch
            
        Returns:
            List of trade data
            [
                {
                    "price": float,
                    "quantity": float,
                    "timestamp": int,
                    "side": "BUY" | "SELL"
                },
                ...
            ]
        """
        try:
            symbol = self._normalize_symbol(symbol)
            logger.info(f"Fetching recent trades for {symbol} (limit: {limit})")
            
            client = get_httpx_client()
            
            url = f"{self.base_url}/v1/market/aggTrade/{symbol}?limit={limit}"
            response = client.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch trades: {response.status_code}")
                return []
            
            data = response.json()
            
            if not data.get("success"):
                logger.error(f"Trades API error: {data.get('message')}")
                return []
            
            trades_data = data.get("data", [])
            
            # Parse trades
            trades = []
            for trade in trades_data:
                trades.append({
                    "price": float(trade.get("price", 0)),
                    "quantity": float(trade.get("quantity", 0)),
                    "timestamp": int(trade.get("timestamp", 0)),
                    "side": "BUY" if trade.get("isBuyerMaker") else "SELL"
                })
            
            logger.info(f"Fetched {len(trades)} recent trades")
            
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching recent trades: {str(e)}")
            return []
    
    def _get_default_quote(self) -> dict:
        """Return default quote structure."""
        return {
            "bid": 0,
            "ask": 0,
            "open": 0,
            "high": 0,
            "low": 0,
            "ltp": 0,
            "prev_close": 0,
            "volume": 0,
            "oi": 0,
            "mark_price": 0,
            "index_price": 0,
            "funding_rate": 0
        }
    
    def _get_default_depth(self) -> dict:
        """Return default depth structure."""
        return {
            "bids": [{"price": 0, "quantity": 0} for _ in range(5)],
            "asks": [{"price": 0, "quantity": 0} for _ in range(5)],
            "totalbuyqty": 0,
            "totalsellqty": 0
        }
    
    def _get_empty_dataframe(self) -> pd.DataFrame:
        """Return empty DataFrame with correct columns."""
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
```

## Exchange Info API

```python
def get_exchange_info(symbol: Optional[str] = None) -> dict:
    """
    Get exchange information and contract specifications.
    
    Args:
        symbol: Optional symbol filter
        
    Returns:
        {
            "success": bool,
            "data": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "pricePrecision": 2,
                    "quantityPrecision": 3,
                    "minQuantity": 0.001,
                    "maxQuantity": 1000,
                    "minNotional": 10,
                    "maxLeverage": 25,
                    "marginAssets": ["USDT", "INR"],
                    "tickSize": 0.01
                },
                ...
            ]
        }
    """
    try:
        logger.info("Fetching exchange info")
        
        client = get_httpx_client()
        
        url = "https://api.pi42.com/v1/exchange/exchangeInfo"
        if symbol:
            url = f"{url}?symbol={symbol}"
        
        response = client.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch exchange info: {response.status_code}")
            return {"success": False, "data": []}
        
        data = response.json()
        
        logger.info(f"Fetched exchange info for {len(data.get('data', []))} symbols")
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching exchange info: {str(e)}")
        return {"success": False, "data": []}
```

## Price Precision Handling

```python
def format_price(price: float, symbol: str) -> float:
    """
    Format price according to symbol's tick size.
    
    Args:
        price: Price to format
        symbol: Trading symbol
        
    Returns:
        Formatted price
    """
    try:
        # Get exchange info for symbol
        exchange_info = get_exchange_info(symbol)
        
        if not exchange_info.get("success"):
            return round(price, 2)  # Default to 2 decimals
        
        symbols_data = exchange_info.get("data", [])
        
        for symbol_data in symbols_data:
            if symbol_data.get("symbol") == symbol:
                tick_size = float(symbol_data.get("tickSize", 0.01))
                
                # Round to nearest tick size
                return round(price / tick_size) * tick_size
        
        return round(price, 2)
        
    except Exception as e:
        logger.error(f"Error formatting price: {str(e)}")
        return round(price, 2)


def format_quantity(quantity: float, symbol: str) -> float:
    """
    Format quantity according to symbol's precision.
    
    Args:
        quantity: Quantity to format
        symbol: Trading symbol
        
    Returns:
        Formatted quantity
    """
    try:
        # Get exchange info for symbol
        exchange_info = get_exchange_info(symbol)
        
        if not exchange_info.get("success"):
            return round(quantity, 3)  # Default to 3 decimals
        
        symbols_data = exchange_info.get("data", [])
        
        for symbol_data in symbols_data:
            if symbol_data.get("symbol") == symbol:
                precision = int(symbol_data.get("quantityPrecision", 3))
                return round(quantity, precision)
        
        return round(quantity, 3)
        
    except Exception as e:
        logger.error(f"Error formatting quantity: {str(e)}")
        return round(quantity, 3)
```

## Testing

```python
def test_get_quotes():
    """Test quote fetching."""
    broker_data = BrokerData(auth_token)
    quotes = broker_data.get_quotes("BTCUSDT")
    
    assert quotes["ltp"] > 0
    assert quotes["mark_price"] > 0
    assert "funding_rate" in quotes


def test_get_depth():
    """Test depth fetching."""
    broker_data = BrokerData(auth_token)
    depth = broker_data.get_depth("BTCUSDT")
    
    assert len(depth["bids"]) == 5
    assert len(depth["asks"]) == 5
    assert depth["bids"][0]["price"] > 0


def test_get_history():
    """Test historical data."""
    broker_data = BrokerData(auth_token)
    df = broker_data.get_history("BTCUSDT", "PI42", "1h", "2024-01-01", "2024-01-02")
    
    assert not df.empty
    assert "timestamp" in df.columns
    assert "close" in df.columns


def test_exchange_info():
    """Test exchange info."""
    info = get_exchange_info("BTCUSDT")
    
    assert info.get("success") == True
    assert len(info.get("data", [])) > 0
```

## Key Features

### 1. Mark Price vs Last Price
- **Last Price**: Actual traded price
- **Mark Price**: Fair price used for margin calculation and liquidation
- Always use mark price for risk calculations

### 2. Funding Rate
- Updated every 8 hours
- Positive rate: Longs pay shorts
- Negative rate: Shorts pay longs
- Critical for position cost calculation

### 3. 24/7 Data
- No market hours restrictions
- Continuous price updates
- Historical data available anytime

### 4. Precision Handling
- BTC: 8 decimal places for quantity
- USDT: 2 decimal places for price
- Must respect tick size and lot size

## Next Steps

1. Implement `data.py` with all functions
2. Add exchange info caching
3. Implement price/quantity formatting
4. Add funding rate tracking
5. Test with various symbols
6. Document all data structures
