# Pi42 Master Contract & Database Implementation Plan

## Overview

Unlike stock brokers that require daily CSV downloads, Pi42 provides contract specifications via API. This document details the master contract implementation for crypto futures.

## Key Differences from Stock Brokers

| Aspect | Stock Brokers | Pi42 Crypto |
|--------|--------------|-------------|
| **Data Source** | Daily CSV files | Real-time API |
| **Update Frequency** | Daily download | On-demand fetch |
| **Expiry Dates** | Monthly/Weekly | Perpetual (no expiry) |
| **Strike Prices** | Options only | Not applicable |
| **Lot Size** | Fixed by exchange | Minimum quantity |
| **Exchanges** | Multiple (NSE, BSE, NFO) | Single (Pi42) |
| **Symbol Format** | Complex (NIFTY24JAN24000CE) | Simple (BTCUSDT) |

## Database Schema Extensions

### 1. Extend SymToken Table

```sql
-- Add crypto-specific fields to existing symtoken table
ALTER TABLE symtoken ADD COLUMN broker_type VARCHAR(20) DEFAULT 'IN_stock';
ALTER TABLE symtoken ADD COLUMN min_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN max_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN price_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN quantity_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN margin_assets TEXT;  -- JSON: ["USDT", "INR"]
ALTER TABLE symtoken ADD COLUMN max_leverage INTEGER;
ALTER TABLE symtoken ADD COLUMN base_asset VARCHAR(10);
ALTER TABLE symtoken ADD COLUMN quote_asset VARCHAR(10);
ALTER TABLE symtoken ADD COLUMN contract_type VARCHAR(20);  -- PERPETUAL
ALTER TABLE symtoken ADD COLUMN min_notional FLOAT;  -- Minimum order value
ALTER TABLE symtoken ADD COLUMN maintenance_margin_rate FLOAT;

-- Add index for crypto queries
CREATE INDEX idx_broker_type ON symtoken(broker_type);
CREATE INDEX idx_base_asset ON symtoken(base_asset);
```

### 2. New Crypto-Specific Tables

#### Funding Rate History
```sql
CREATE TABLE funding_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(50) NOT NULL,
    funding_rate FLOAT NOT NULL,
    funding_time DATETIME NOT NULL,
    mark_price FLOAT,
    index_price FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, funding_time)
);

CREATE INDEX idx_funding_symbol_time ON funding_rates(symbol, funding_time);
```

#### Liquidation History
```sql
CREATE TABLE liquidations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- LONG/SHORT
    quantity FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    liquidation_price FLOAT NOT NULL,
    loss FLOAT NOT NULL,
    margin_asset VARCHAR(10),
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE INDEX idx_liquidation_user ON liquidations(user_id);
CREATE INDEX idx_liquidation_symbol ON liquidations(symbol);
```

#### Margin Operations
```sql
CREATE TABLE margin_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,  -- ADD/REDUCE
    amount FLOAT NOT NULL,
    margin_asset VARCHAR(10) NOT NULL,
    leverage_before INTEGER,
    leverage_after INTEGER,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE INDEX idx_margin_ops_user ON margin_operations(user_id);
CREATE INDEX idx_margin_ops_symbol ON margin_operations(symbol);
```

#### Leverage Settings
```sql
CREATE TABLE leverage_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    leverage INTEGER NOT NULL,
    margin_mode VARCHAR(10) NOT NULL,  -- ISOLATED/CROSS
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, symbol),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE INDEX idx_leverage_user_symbol ON leverage_settings(user_id, symbol);
```

## Implementation: `broker/pi42/database/master_contract_db.py`

```python
"""
Pi42 Master Contract Database Module

Handles contract specifications and symbol management for crypto futures.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Column, Float, Index, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from extensions import socketio
from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class SymToken(Base):
    """Extended SymToken model with crypto-specific fields."""
    
    __tablename__ = "symtoken"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    brsymbol = Column(String, nullable=False, index=True)
    name = Column(String)
    exchange = Column(String, index=True)
    brexchange = Column(String, index=True)
    token = Column(String, index=True)
    expiry = Column(String)
    strike = Column(Float)
    lotsize = Column(Integer)
    instrumenttype = Column(String)
    tick_size = Column(Float)
    
    # Crypto-specific fields
    broker_type = Column(String, default="IN_stock")
    min_quantity = Column(Float)
    max_quantity = Column(Float)
    price_precision = Column(Integer)
    quantity_precision = Column(Integer)
    margin_assets = Column(String)  # JSON string
    max_leverage = Column(Integer)
    base_asset = Column(String)
    quote_asset = Column(String)
    contract_type = Column(String)
    min_notional = Column(Float)
    maintenance_margin_rate = Column(Float)
    
    __table_args__ = (
        Index("idx_symbol_exchange", "symbol", "exchange"),
        Index("idx_broker_type", "broker_type"),
    )


def init_db():
    """Initialize database tables."""
    logger.info("Initializing Pi42 Master Contract DB")
    Base.metadata.create_all(bind=engine)


def get_exchange_info() -> Dict:
    """
    Fetch exchange information from Pi42 API.
    
    Returns:
        Dictionary with contract specifications
    """
    try:
        logger.info("Fetching Pi42 exchange info")
        
        client = get_httpx_client()
        
        response = client.get(
            "https://api.pi42.com/v1/exchange/exchangeInfo",
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch exchange info: {response.status_code}")
            return {"success": False, "data": []}
        
        data = response.json()
        
        logger.info(f"Fetched info for {len(data.get('data', []))} contracts")
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching exchange info: {str(e)}")
        return {"success": False, "data": []}


def process_exchange_info(exchange_data: Dict) -> List[Dict]:
    """
    Process exchange info into database format.
    
    Args:
        exchange_data: Raw exchange info from API
        
    Returns:
        List of processed contract dictionaries
    """
    try:
        if not exchange_data.get("success"):
            logger.error("Exchange info not successful")
            return []
        
        contracts = exchange_data.get("data", [])
        processed = []
        
        for contract in contracts:
            # Extract contract details
            symbol = contract.get("symbol", "")
            base_asset = contract.get("baseAsset", "")
            quote_asset = contract.get("quoteAsset", "")
            
            # Build processed contract
            processed_contract = {
                # Standard fields
                "symbol": symbol,
                "brsymbol": symbol,  # Same for crypto
                "name": f"{base_asset}/{quote_asset} Perpetual",
                "exchange": "PI42",
                "brexchange": "PI42",
                "token": symbol,  # Use symbol as token
                "expiry": "",  # Perpetual - no expiry
                "strike": 0.0,  # Not applicable
                "lotsize": int(contract.get("minQuantity", 0) * 1000),  # Convert to integer
                "instrumenttype": "PERPETUAL",
                "tick_size": float(contract.get("tickSize", 0.01)),
                
                # Crypto-specific fields
                "broker_type": "CRYPTO_futures",
                "min_quantity": float(contract.get("minQuantity", 0)),
                "max_quantity": float(contract.get("maxQuantity", 0)),
                "price_precision": int(contract.get("pricePrecision", 2)),
                "quantity_precision": int(contract.get("quantityPrecision", 3)),
                "margin_assets": json.dumps(contract.get("marginAssets", ["USDT"])),
                "max_leverage": int(contract.get("maxLeverage", 25)),
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "contract_type": "PERPETUAL",
                "min_notional": float(contract.get("minNotional", 10)),
                "maintenance_margin_rate": float(contract.get("maintenanceMarginRate", 0.01))
            }
            
            processed.append(processed_contract)
        
        logger.info(f"Processed {len(processed)} contracts")
        
        return processed
        
    except Exception as e:
        logger.error(f"Error processing exchange info: {str(e)}")
        return []


def delete_pi42_contracts():
    """Delete existing Pi42 contracts from database."""
    try:
        logger.info("Deleting existing Pi42 contracts")
        
        # Delete only Pi42 contracts, keep stock broker data
        deleted = SymToken.query.filter_by(broker_type="CRYPTO_futures").delete()
        db_session.commit()
        
        logger.info(f"Deleted {deleted} Pi42 contracts")
        
    except Exception as e:
        logger.error(f"Error deleting Pi42 contracts: {str(e)}")
        db_session.rollback()


def bulk_insert_contracts(contracts: List[Dict]):
    """
    Bulk insert contracts into database.
    
    Args:
        contracts: List of processed contract dictionaries
    """
    try:
        logger.info(f"Bulk inserting {len(contracts)} contracts")
        
        # Filter out existing contracts
        existing_symbols = {
            result.symbol for result in 
            db_session.query(SymToken.symbol).filter_by(broker_type="CRYPTO_futures").all()
        }
        
        new_contracts = [
            contract for contract in contracts 
            if contract["symbol"] not in existing_symbols
        ]
        
        if new_contracts:
            db_session.bulk_insert_mappings(SymToken, new_contracts)
            db_session.commit()
            logger.info(f"Inserted {len(new_contracts)} new contracts")
        else:
            logger.info("No new contracts to insert")
            
    except Exception as e:
        logger.error(f"Error bulk inserting contracts: {str(e)}")
        db_session.rollback()


def master_contract_download() -> Dict:
    """
    Main function to download and update Pi42 master contracts.
    
    Returns:
        Status dictionary
    """
    try:
        logger.info("Starting Pi42 master contract download")
        
        # Emit progress
        socketio.emit('master_contract_download', {
            'status': 'downloading',
            'broker': 'pi42',
            'message': 'Fetching contract specifications from Pi42...'
        })
        
        # Fetch exchange info
        exchange_data = get_exchange_info()
        
        if not exchange_data.get("success"):
            error_msg = "Failed to fetch exchange info"
            logger.error(error_msg)
            socketio.emit('master_contract_download', {
                'status': 'error',
                'broker': 'pi42',
                'message': error_msg
            })
            return {"status": "error", "message": error_msg}
        
        # Emit progress
        socketio.emit('master_contract_download', {
            'status': 'processing',
            'broker': 'pi42',
            'message': 'Processing contract data...'
        })
        
        # Process contracts
        contracts = process_exchange_info(exchange_data)
        
        if not contracts:
            error_msg = "No contracts to process"
            logger.error(error_msg)
            socketio.emit('master_contract_download', {
                'status': 'error',
                'broker': 'pi42',
                'message': error_msg
            })
            return {"status": "error", "message": error_msg}
        
        # Emit progress
        socketio.emit('master_contract_download', {
            'status': 'updating',
            'broker': 'pi42',
            'message': f'Updating database with {len(contracts)} contracts...'
        })
        
        # Delete old contracts
        delete_pi42_contracts()
        
        # Insert new contracts
        bulk_insert_contracts(contracts)
        
        # Emit completion
        socketio.emit('master_contract_download', {
            'status': 'complete',
            'broker': 'pi42',
            'message': f'Successfully updated {len(contracts)} contracts'
        })
        
        logger.info("Pi42 master contract download completed successfully")
        
        return {
            "status": "success",
            "message": f"Updated {len(contracts)} contracts",
            "count": len(contracts)
        }
        
    except Exception as e:
        error_msg = f"Master contract download failed: {str(e)}"
        logger.error(error_msg)
        
        socketio.emit('master_contract_download', {
            'status': 'error',
            'broker': 'pi42',
            'message': error_msg
        })
        
        return {"status": "error", "message": error_msg}


def get_contract_info(symbol: str) -> Optional[SymToken]:
    """
    Get contract information for symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        SymToken object or None
    """
    try:
        contract = SymToken.query.filter_by(
            symbol=symbol,
            broker_type="CRYPTO_futures"
        ).first()
        
        return contract
        
    except Exception as e:
        logger.error(f"Error getting contract info: {str(e)}")
        return None


def get_all_contracts() -> List[SymToken]:
    """
    Get all Pi42 contracts.
    
    Returns:
        List of SymToken objects
    """
    try:
        contracts = SymToken.query.filter_by(broker_type="CRYPTO_futures").all()
        return contracts
        
    except Exception as e:
        logger.error(f"Error getting all contracts: {str(e)}")
        return []


def get_contracts_by_base_asset(base_asset: str) -> List[SymToken]:
    """
    Get contracts by base asset (e.g., BTC, ETH).
    
    Args:
        base_asset: Base asset symbol
        
    Returns:
        List of SymToken objects
    """
    try:
        contracts = SymToken.query.filter_by(
            base_asset=base_asset.upper(),
            broker_type="CRYPTO_futures"
        ).all()
        
        return contracts
        
    except Exception as e:
        logger.error(f"Error getting contracts by base asset: {str(e)}")
        return []


def search_contracts(query: str) -> List[SymToken]:
    """
    Search contracts by symbol or name.
    
    Args:
        query: Search query
        
    Returns:
        List of matching SymToken objects
    """
    try:
        query = query.upper()
        
        contracts = SymToken.query.filter(
            SymToken.broker_type == "CRYPTO_futures",
            (SymToken.symbol.like(f"%{query}%") | SymToken.name.like(f"%{query}%"))
        ).limit(50).all()
        
        return contracts
        
    except Exception as e:
        logger.error(f"Error searching contracts: {str(e)}")
        return []


def validate_order_params(symbol: str, quantity: float, price: float) -> Dict:
    """
    Validate order parameters against contract specifications.
    
    Args:
        symbol: Trading symbol
        quantity: Order quantity
        price: Order price
        
    Returns:
        Validation result dictionary
    """
    try:
        contract = get_contract_info(symbol)
        
        if not contract:
            return {
                "valid": False,
                "error": f"Contract not found: {symbol}"
            }
        
        # Validate quantity
        if quantity < contract.min_quantity:
            return {
                "valid": False,
                "error": f"Quantity below minimum: {contract.min_quantity}"
            }
        
        if quantity > contract.max_quantity:
            return {
                "valid": False,
                "error": f"Quantity above maximum: {contract.max_quantity}"
            }
        
        # Validate notional value
        notional = quantity * price
        if notional < contract.min_notional:
            return {
                "valid": False,
                "error": f"Order value below minimum: {contract.min_notional}"
            }
        
        # Validate price precision
        price_str = str(price)
        if '.' in price_str:
            decimals = len(price_str.split('.')[1])
            if decimals > contract.price_precision:
                return {
                    "valid": False,
                    "error": f"Price precision exceeds maximum: {contract.price_precision}"
                }
        
        # Validate quantity precision
        qty_str = str(quantity)
        if '.' in qty_str:
            decimals = len(qty_str.split('.')[1])
            if decimals > contract.quantity_precision:
                return {
                    "valid": False,
                    "error": f"Quantity precision exceeds maximum: {contract.quantity_precision}"
                }
        
        return {"valid": True}
        
    except Exception as e:
        logger.error(f"Error validating order params: {str(e)}")
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}"
        }
```

## Funding Rate Tracking

```python
def store_funding_rate(symbol: str, funding_rate: float, mark_price: float, 
                       index_price: float, funding_time: datetime):
    """
    Store funding rate in database.
    
    Args:
        symbol: Trading symbol
        funding_rate: Funding rate
        mark_price: Mark price at funding time
        index_price: Index price at funding time
        funding_time: Funding timestamp
    """
    try:
        from database.symbol import db_session
        
        # Check if already exists
        existing = db_session.execute(
            "SELECT id FROM funding_rates WHERE symbol = ? AND funding_time = ?",
            (symbol, funding_time)
        ).fetchone()
        
        if existing:
            logger.debug(f"Funding rate already stored for {symbol} at {funding_time}")
            return
        
        # Insert new funding rate
        db_session.execute(
            """
            INSERT INTO funding_rates (symbol, funding_rate, mark_price, index_price, funding_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (symbol, funding_rate, mark_price, index_price, funding_time)
        )
        db_session.commit()
        
        logger.info(f"Stored funding rate for {symbol}: {funding_rate}")
        
    except Exception as e:
        logger.error(f"Error storing funding rate: {str(e)}")
        db_session.rollback()


def get_funding_history(symbol: str, limit: int = 100) -> List[Dict]:
    """
    Get funding rate history for symbol.
    
    Args:
        symbol: Trading symbol
        limit: Number of records to fetch
        
    Returns:
        List of funding rate records
    """
    try:
        from database.symbol import db_session
        
        results = db_session.execute(
            """
            SELECT symbol, funding_rate, mark_price, index_price, funding_time
            FROM funding_rates
            WHERE symbol = ?
            ORDER BY funding_time DESC
            LIMIT ?
            """,
            (symbol, limit)
        ).fetchall()
        
        history = []
        for row in results:
            history.append({
                "symbol": row[0],
                "funding_rate": row[1],
                "mark_price": row[2],
                "index_price": row[3],
                "funding_time": row[4]
            })
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting funding history: {str(e)}")
        return []
```

## Testing

```python
def test_master_contract_download():
    """Test master contract download."""
    result = master_contract_download()
    assert result["status"] == "success"
    assert result["count"] > 0


def test_get_contract_info():
    """Test contract info retrieval."""
    contract = get_contract_info("BTCUSDT")
    assert contract is not None
    assert contract.broker_type == "CRYPTO_futures"
    assert contract.max_leverage > 0


def test_validate_order_params():
    """Test order parameter validation."""
    # Valid order
    result = validate_order_params("BTCUSDT", 0.5, 50000)
    assert result["valid"] == True
    
    # Invalid quantity (too small)
    result = validate_order_params("BTCUSDT", 0.0001, 50000)
    assert result["valid"] == False


def test_search_contracts():
    """Test contract search."""
    contracts = search_contracts("BTC")
    assert len(contracts) > 0
    assert all("BTC" in c.symbol for c in contracts)
```

## Key Features

### 1. Real-Time Updates
- No daily CSV downloads needed
- Fetch on-demand from API
- Cache in database for performance

### 2. Validation
- Validate quantity against min/max
- Validate price precision
- Validate notional value
- Prevent invalid orders

### 3. Funding Rate Tracking
- Store historical funding rates
- Track mark price and index price
- Calculate funding costs

### 4. Search & Discovery
- Search by symbol or name
- Filter by base asset
- Get all available contracts

## Next Steps

1. Implement `master_contract_db.py`
2. Create database migration scripts
3. Add funding rate tracking
4. Implement validation functions
5. Test with Pi42 API
6. Document contract specifications
