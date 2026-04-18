# Phase 1: Foundation (Week 1-2)

**Goal:** Set up core infrastructure for crypto support

**Prerequisites:**
- Pi42 test account created
- API credentials obtained (API Key + Secret)
- Development environment set up

---

## Week 1: Core Architecture

### Day 1: Broker Type System

#### Step 1.1: Add broker_type to Database Schema

**File:** `database/symbol_db.py`

```python
# Add to symtoken table definition
broker_type = Column(String(20), default='IN_stock')  # 'IN_stock' or 'CRYPTO_futures'
```

**Migration SQL:**
```sql
ALTER TABLE symtoken ADD COLUMN broker_type VARCHAR(20) DEFAULT 'IN_stock';
CREATE INDEX idx_broker_type ON symtoken(broker_type);
```

**Run migration:**
```bash
uv run python -c "
from database.symbol_db import db
from sqlalchemy import text

with db.engine.connect() as conn:
    conn.execute(text(\"ALTER TABLE symtoken ADD COLUMN broker_type VARCHAR(20) DEFAULT 'IN_stock'\"))
    conn.execute(text(\"CREATE INDEX idx_broker_type ON symtoken(broker_type)\"))
    conn.commit()
"
```

**Verify:**
```bash
uv run python -c "
from database.symbol_db import db
from sqlalchemy import inspect

inspector = inspect(db.engine)
columns = [col['name'] for col in inspector.get_columns('symtoken')]
print('broker_type' in columns)
"
```

#### Step 1.2: Create Broker Type Detection Utility

**File:** `utils/broker_utils.py` (create new file)

```python
"""Broker type detection utilities."""

STOCK_BROKERS = ['zerodha', 'dhan', 'fyers', 'kotak', 'angel']
CRYPTO_BROKERS = ['pi42']

def get_broker_type(broker_name: str) -> str:
    """
    Get broker type from broker name.
    
    Args:
        broker_name: Broker identifier
        
    Returns:
        'IN_stock' or 'CRYPTO_futures'
    """
    broker_lower = broker_name.lower()
    
    if broker_lower in CRYPTO_BROKERS:
        return 'CRYPTO_futures'
    elif broker_lower in STOCK_BROKERS:
        return 'IN_stock'
    else:
        # Default to stock for unknown brokers
        return 'IN_stock'


def is_crypto_broker(broker_name: str) -> bool:
    """Check if broker is crypto exchange."""
    return get_broker_type(broker_name) == 'CRYPTO_futures'


def is_stock_broker(broker_name: str) -> bool:
    """Check if broker is stock exchange."""
    return get_broker_type(broker_name) == 'IN_stock'
```

**Test:**
```bash
uv run python -c "
from utils.broker_utils import get_broker_type, is_crypto_broker

assert get_broker_type('pi42') == 'CRYPTO_futures'
assert get_broker_type('zerodha') == 'IN_stock'
assert is_crypto_broker('pi42') == True
assert is_crypto_broker('zerodha') == False
print('✓ Broker type detection working')
"
```

#### Step 1.3: Update Broker Selection Logic

**File:** `blueprints/auth.py`

Find the broker selection/validation logic and add broker type detection:

```python
from utils.broker_utils import get_broker_type

# In login or broker selection endpoint
broker_name = request.form.get('broker')
broker_type = get_broker_type(broker_name)

# Store broker_type in session or user settings
session['broker_type'] = broker_type
```

**Verify:** Login with different brokers and check session contains correct broker_type

---

### Day 2: Database Schema Extensions

#### Step 2.1: Extend symtoken Table

**Migration SQL:**
```sql
-- Add crypto-specific fields to symtoken
ALTER TABLE symtoken ADD COLUMN min_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN max_quantity FLOAT;
ALTER TABLE symtoken ADD COLUMN price_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN quantity_precision INTEGER;
ALTER TABLE symtoken ADD COLUMN margin_assets TEXT;
ALTER TABLE symtoken ADD COLUMN max_leverage INTEGER;
ALTER TABLE symtoken ADD COLUMN base_asset VARCHAR(10);
ALTER TABLE symtoken ADD COLUMN quote_asset VARCHAR(10);
ALTER TABLE symtoken ADD COLUMN contract_type VARCHAR(20);
ALTER TABLE symtoken ADD COLUMN min_notional FLOAT;
ALTER TABLE symtoken ADD COLUMN maintenance_margin_rate FLOAT;

-- Create indexes
CREATE INDEX idx_base_asset ON symtoken(base_asset);
CREATE INDEX idx_quote_asset ON symtoken(quote_asset);
```

**Run migration:**
```bash
uv run python -c "
from database.symbol_db import db
from sqlalchemy import text

migrations = [
    'ALTER TABLE symtoken ADD COLUMN min_quantity FLOAT',
    'ALTER TABLE symtoken ADD COLUMN max_quantity FLOAT',
    'ALTER TABLE symtoken ADD COLUMN price_precision INTEGER',
    'ALTER TABLE symtoken ADD COLUMN quantity_precision INTEGER',
    'ALTER TABLE symtoken ADD COLUMN margin_assets TEXT',
    'ALTER TABLE symtoken ADD COLUMN max_leverage INTEGER',
    'ALTER TABLE symtoken ADD COLUMN base_asset VARCHAR(10)',
    'ALTER TABLE symtoken ADD COLUMN quote_asset VARCHAR(10)',
    'ALTER TABLE symtoken ADD COLUMN contract_type VARCHAR(20)',
    'ALTER TABLE symtoken ADD COLUMN min_notional FLOAT',
    'ALTER TABLE symtoken ADD COLUMN maintenance_margin_rate FLOAT',
    'CREATE INDEX idx_base_asset ON symtoken(base_asset)',
    'CREATE INDEX idx_quote_asset ON symtoken(quote_asset)'
]

with db.engine.connect() as conn:
    for migration in migrations:
        try:
            conn.execute(text(migration))
            print(f'✓ {migration[:50]}...')
        except Exception as e:
            print(f'✗ {migration[:50]}... ({e})')
    conn.commit()
"
```

#### Step 2.2: Create Crypto-Specific Tables

**File:** `database/crypto_db.py` (create new file)

```python
"""Crypto-specific database models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from database.symbol_db import db

class FundingRate(db.Model):
    """Funding rate history."""
    __tablename__ = 'funding_rates'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False, index=True)
    funding_rate = Column(Float, nullable=False)
    funding_time = Column(DateTime, nullable=False)
    mark_price = Column(Float)
    index_price = Column(Float)
    created_at = Column(DateTime, default=func.now())


class Liquidation(db.Model):
    """Liquidation history."""
    __tablename__ = 'liquidations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    liquidation_price = Column(Float, nullable=False)
    loss = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)


class MarginOperation(db.Model):
    """Margin add/reduce history."""
    __tablename__ = 'margin_operations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    operation = Column(String(10), nullable=False)  # 'ADD' or 'REDUCE'
    amount = Column(Float, nullable=False)
    margin_asset = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=func.now())


class LeverageSetting(db.Model):
    """User leverage preferences."""
    __tablename__ = 'leverage_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    leverage = Column(Integer, nullable=False)
    margin_mode = Column(String(10), nullable=False)  # 'ISOLATED' or 'CROSS'
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Create tables
def init_crypto_tables():
    """Initialize crypto-specific tables."""
    db.create_all()
```

**Run table creation:**
```bash
uv run python -c "
from database.crypto_db import init_crypto_tables
init_crypto_tables()
print('✓ Crypto tables created')
"
```

**Verify:**
```bash
uv run python -c "
from database.symbol_db import db
from sqlalchemy import inspect

inspector = inspect(db.engine)
tables = inspector.get_table_names()

required_tables = ['funding_rates', 'liquidations', 'margin_operations', 'leverage_settings']
for table in required_tables:
    if table in tables:
        print(f'✓ {table} exists')
    else:
        print(f'✗ {table} missing')
"
```

---

### Day 3: Environment Configuration

#### Step 3.1: Add Pi42 Configuration to .env

**File:** `.env`

Add these lines:
```bash
# Pi42 Configuration
PI42_API_KEY=your_api_key_here
PI42_API_SECRET=your_api_secret_here
PI42_BASE_URL=https://fapi.pi42.com
PI42_WS_URL=wss://fawss-uds.pi42.com/auth-stream
PI42_PUBLIC_WS_URL=wss://fawss.pi42.com/market-stream

# Add pi42 to valid brokers
VALID_BROKERS=zerodha,dhan,fyers,kotak,angel,pi42
```

#### Step 3.2: Create Pi42 Directory Structure

```bash
mkdir -p broker/pi42/api
mkdir -p broker/pi42/database
mkdir -p broker/pi42/mapping
mkdir -p broker/pi42/streaming
```

**Create __init__.py files:**
```bash
touch broker/pi42/__init__.py
touch broker/pi42/api/__init__.py
touch broker/pi42/database/__init__.py
touch broker/pi42/mapping/__init__.py
touch broker/pi42/streaming/__init__.py
```

#### Step 3.3: Create plugin.json

**File:** `broker/pi42/plugin.json`

```json
{
  "broker_name": "pi42",
  "broker_display_name": "Pi42",
  "broker_type": "CRYPTO_futures",
  "version": "1.0.0",
  "description": "Pi42 cryptocurrency futures exchange integration",
  "auth_type": "HMAC-SHA256",
  "supports": {
    "orders": true,
    "positions": true,
    "market_data": true,
    "historical_data": true,
    "websocket": true,
    "leverage": true,
    "margin_management": true,
    "funding_rates": true
  },
  "order_types": ["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"],
  "margin_modes": ["ISOLATED", "CROSS"],
  "margin_assets": ["USDT", "INR"],
  "max_leverage": 25,
  "rate_limits": {
    "place_order": "20/second",
    "cancel_order": "30/minute",
    "default": "60/minute"
  }
}
```

**Verify structure:**
```bash
ls -R broker/pi42/
```

---

### Day 4: Authentication Foundation

#### Step 4.1: Create Pi42Auth Class

**File:** `broker/pi42/api/auth_api.py`

```python
"""Pi42 authentication implementation."""

import hmac
import hashlib
import time
import os
from typing import Dict, Tuple, Optional


class Pi42Auth:
    """Pi42 HMAC-SHA256 authentication."""
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Pi42 authentication.
        
        Args:
            api_key: Pi42 API key
            api_secret: Pi42 API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = os.getenv('PI42_BASE_URL', 'https://fapi.pi42.com')
    
    def generate_signature(self, data: str) -> str:
        """
        Generate HMAC-SHA256 signature.
        
        Args:
            data: Data to sign
            
        Returns:
            Hex signature string
        """
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def sign_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> Tuple[Dict[str, str], Optional[Dict]]:
        """
        Sign API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            body: Request body
            
        Returns:
            Tuple of (headers, signed_body)
        """
        timestamp = str(int(time.time() * 1000))
        
        # Build signature data
        signature_data = f"{method}{endpoint}{timestamp}"
        
        if params:
            # Sort params and append
            sorted_params = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
            signature_data += sorted_params
        
        if body:
            import json
            signature_data += json.dumps(body, separators=(',', ':'))
        
        # Generate signature
        signature = self.generate_signature(signature_data)
        
        # Build headers
        headers = {
            'X-API-KEY': self.api_key,
            'X-SIGNATURE': signature,
            'X-TIMESTAMP': timestamp,
            'Content-Type': 'application/json'
        }
        
        return headers, body


def create_auth_instance(auth_token: str) -> Pi42Auth:
    """
    Create Pi42Auth instance from auth token.
    
    Args:
        auth_token: Encrypted auth token from database
        
    Returns:
        Pi42Auth instance
    """
    # Decrypt auth token to get API key and secret
    from utils.encryption import decrypt_token
    
    decrypted = decrypt_token(auth_token)
    api_key, api_secret = decrypted.split('|')
    
    return Pi42Auth(api_key, api_secret)
```

**Test authentication:**
```bash
uv run python -c "
from broker.pi42.api.auth_api import Pi42Auth

# Test with dummy credentials
auth = Pi42Auth('test_key', 'test_secret')

# Test signature generation
data = 'test_data'
signature = auth.generate_signature(data)
print(f'Signature: {signature}')

# Test request signing
headers, body = auth.sign_request('GET', '/v1/test', params={'symbol': 'BTCUSDT'})
print(f'Headers: {headers}')
print('✓ Authentication module working')
"
```

#### Step 4.2: Create Rate Limiter

**File:** `broker/pi42/api/rate_limiter.py` (create new file)

```python
"""Rate limiting for Pi42 API."""

import time
from collections import deque
from typing import Dict


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.buckets: Dict[str, deque] = {}
        self.limits = {
            'place_order': (20, 1),      # 20 per second
            'cancel_order': (30, 60),    # 30 per minute
            'default': (60, 60)          # 60 per minute
        }
    
    def check_limit(self, endpoint: str) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            endpoint: API endpoint identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        # Get limit for endpoint
        limit, window = self.limits.get(endpoint, self.limits['default'])
        
        # Initialize bucket if needed
        if endpoint not in self.buckets:
            self.buckets[endpoint] = deque()
        
        bucket = self.buckets[endpoint]
        now = time.time()
        
        # Remove old timestamps
        while bucket and bucket[0] < now - window:
            bucket.popleft()
        
        # Check if under limit
        if len(bucket) < limit:
            bucket.append(now)
            return True
        
        return False
    
    def wait_if_needed(self, endpoint: str) -> None:
        """
        Wait if rate limit exceeded.
        
        Args:
            endpoint: API endpoint identifier
        """
        while not self.check_limit(endpoint):
            time.sleep(0.1)


# Global rate limiter instance
rate_limiter = RateLimiter()
```

**Test rate limiter:**
```bash
uv run python -c "
from broker.pi42.api.rate_limiter import rate_limiter
import time

# Test rate limiting
start = time.time()
for i in range(25):
    rate_limiter.wait_if_needed('place_order')
    if i == 19:
        elapsed = time.time() - start
        print(f'First 20 requests: {elapsed:.2f}s')
    elif i == 24:
        elapsed = time.time() - start
        print(f'25 requests: {elapsed:.2f}s (should be >1s)')

print('✓ Rate limiter working')
"
```

---

### Day 5: Test Authentication with Pi42 API

#### Step 5.1: Create Test Script

**File:** `test/test_pi42_auth.py`

```python
"""Test Pi42 authentication."""

import os
import requests
from broker.pi42.api.auth_api import Pi42Auth


def test_authentication():
    """Test authentication with Pi42 API."""
    # Get credentials from environment
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')
    base_url = os.getenv('PI42_BASE_URL')
    
    if not api_key or not api_secret:
        print('⚠ PI42_API_KEY and PI42_API_SECRET not set in .env')
        return False
    
    # Create auth instance
    auth = Pi42Auth(api_key, api_secret)
    
    # Test with account info endpoint
    endpoint = '/v1/account/info'
    headers, _ = auth.sign_request('GET', endpoint)
    
    # Make request
    url = f"{base_url}{endpoint}"
    response = requests.get(url, headers=headers)
    
    print(f'Status: {response.status_code}')
    print(f'Response: {response.text[:200]}')
    
    if response.status_code == 200:
        print('✓ Authentication successful')
        return True
    else:
        print('✗ Authentication failed')
        return False


if __name__ == '__main__':
    test_authentication()
```

**Run test:**
```bash
uv run pytest test/test_pi42_auth.py -v
```

---

## Week 1 Completion Checklist

- [ ] broker_type field added to database
- [ ] Broker type detection utility created
- [ ] Broker selection logic updated
- [ ] symtoken table extended with crypto fields
- [ ] Crypto-specific tables created (funding_rates, liquidations, etc.)
- [ ] Pi42 configuration added to .env
- [ ] Pi42 directory structure created
- [ ] plugin.json created
- [ ] Pi42Auth class implemented
- [ ] Rate limiter implemented
- [ ] Authentication tested with Pi42 API

**Verification Command:**
```bash
uv run python -c "
from database.symbol_db import db
from sqlalchemy import inspect
from utils.broker_utils import get_broker_type
from broker.pi42.api.auth_api import Pi42Auth

# Check database
inspector = inspect(db.engine)
tables = inspector.get_table_names()
columns = [col['name'] for col in inspector.get_columns('symtoken')]

print('Database checks:')
print(f'  ✓ broker_type in symtoken: {\"broker_type\" in columns}')
print(f'  ✓ funding_rates table: {\"funding_rates\" in tables}')
print(f'  ✓ liquidations table: {\"liquidations\" in tables}')

print('\\nBroker type detection:')
print(f'  ✓ pi42 = CRYPTO_futures: {get_broker_type(\"pi42\") == \"CRYPTO_futures\"}')

print('\\nAuthentication:')
print(f'  ✓ Pi42Auth class exists: {Pi42Auth is not None}')

print('\\n✓ Week 1 foundation complete')
"
```

---

## Next: Week 2 - Basic Integration

Continue to `PHASE-1-WEEK-2.md` for:
- Master contract download
- Basic order placement (MARKET/LIMIT)
- Market data API
- Initial testing
