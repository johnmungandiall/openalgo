# Pi42 Testing & Quality Assurance Plan

## Overview

Comprehensive testing strategy for Pi42 crypto futures integration, covering unit tests, integration tests, end-to-end tests, and user acceptance testing.

## Testing Pyramid

```
                    /\
                   /  \
                  / E2E \
                 /  Tests \
                /----------\
               /            \
              /  Integration \
             /     Tests      \
            /------------------\
           /                    \
          /     Unit Tests       \
         /________________________\
```

## 1. Unit Tests

### Backend Unit Tests

#### Authentication Tests
**File:** `test/test_pi42_auth.py`

```python
import pytest
from broker.pi42.api.auth_api import (
    Pi42Auth,
    authenticate_broker,
    generate_signature
)

def test_signature_generation():
    """Test HMAC-SHA256 signature generation."""
    auth = Pi42Auth("test_key", "test_secret")
    data = "test_data"
    signature = auth.generate_signature(data)
    
    assert len(signature) == 64  # SHA256 hex is 64 chars
    assert isinstance(signature, str)


def test_timestamp_generation():
    """Test timestamp generation."""
    auth = Pi42Auth("test_key", "test_secret")
    timestamp = auth.get_timestamp()
    
    assert timestamp > 0
    assert len(str(timestamp)) == 13  # Milliseconds


def test_sign_get_request():
    """Test GET request signing."""
    auth = Pi42Auth("test_key", "test_secret")
    headers, params = auth.sign_request("GET", "/test", params={"key": "value"})
    
    assert "api-key" in headers
    assert "signature" in headers
    assert "timestamp" in params


def test_sign_post_request():
    """Test POST request signing."""
    auth = Pi42Auth("test_key", "test_secret")
    headers, body = auth.sign_request("POST", "/test", body={"key": "value"})
    
    assert "api-key" in headers
    assert "signature" in headers
    assert "Content-Type" in headers
    assert "timestamp" in body


def test_authenticate_broker_invalid_credentials():
    """Test authentication with invalid credentials."""
    auth_token, error = authenticate_broker("invalid_key", "invalid_secret")
    
    assert auth_token is None
    assert error is not None
```

#### Order Management Tests
**File:** `test/test_pi42_orders.py`

```python
import pytest
from broker.pi42.api.order_api import (
    place_order_api,
    modify_order,
    cancel_order,
    get_open_position
)

@pytest.fixture
def mock_auth_token():
    return "test_key:::test_secret:::https://fapi.pi42.com"


@pytest.fixture
def sample_order_data():
    return {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "quantity": "0.5",
        "pricetype": "LIMIT",
        "price": "50000",
        "leverage": 10,
        "margin_mode": "ISOLATED",
        "margin_asset": "USDT"
    }


def test_place_order_validation(sample_order_data):
    """Test order data validation."""
    # Missing required field
    invalid_data = sample_order_data.copy()
    del invalid_data["symbol"]
    
    with pytest.raises(KeyError):
        place_order_api(invalid_data, "mock_token")


def test_leverage_validation():
    """Test leverage validation."""
    from broker.pi42.mapping.transform_data import transform_order_data
    
    data = {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "quantity": "0.5",
        "pricetype": "MARKET",
        "leverage": 30  # Invalid - exceeds max
    }
    
    # Should raise validation error
    with pytest.raises(ValueError):
        validate_leverage(data["leverage"])


def test_calculate_liquidation_price():
    """Test liquidation price calculation."""
    from broker.pi42.mapping.transform_data import calculate_liquidation_price
    
    # Long position
    liq_price = calculate_liquidation_price(50000, 10, "LONG")
    assert liq_price < 50000
    assert liq_price > 0
    
    # Short position
    liq_price = calculate_liquidation_price(50000, 10, "SHORT")
    assert liq_price > 50000


def test_calculate_unrealized_pnl():
    """Test unrealized PnL calculation."""
    from broker.pi42.mapping.transform_data import calculate_unrealized_pnl
    
    # Long position profit
    pnl = calculate_unrealized_pnl(0.5, 50000, 51000, "LONG")
    assert pnl == 500
    
    # Long position loss
    pnl = calculate_unrealized_pnl(0.5, 50000, 49000, "LONG")
    assert pnl == -500
    
    # Short position profit
    pnl = calculate_unrealized_pnl(0.5, 50000, 49000, "SHORT")
    assert pnl == 500
```

#### Data Transformation Tests
**File:** `test/test_pi42_transform.py`

```python
import pytest
from broker.pi42.mapping.transform_data import (
    transform_order_data,
    map_order_type,
    reverse_map_order_type,
    format_crypto_price,
    format_crypto_quantity
)

def test_transform_order_data():
    """Test order data transformation."""
    openalgo_data = {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "quantity": "0.5",
        "pricetype": "LIMIT",
        "price": "50000",
        "leverage": 10
    }
    
    pi42_data = transform_order_data(openalgo_data)
    
    assert pi42_data["symbol"] == "BTCUSDT"
    assert pi42_data["side"] == "BUY"
    assert pi42_data["type"] == "LIMIT"
    assert pi42_data["quantity"] == 0.5
    assert pi42_data["price"] == 50000
    assert pi42_data["leverage"] == 10


def test_order_type_mapping():
    """Test order type mapping."""
    assert map_order_type("MARKET") == "MARKET"
    assert map_order_type("LIMIT") == "LIMIT"
    assert map_order_type("SL") == "STOP_LIMIT"
    assert map_order_type("SL-M") == "STOP_MARKET"


def test_reverse_order_type_mapping():
    """Test reverse order type mapping."""
    assert reverse_map_order_type("MARKET") == "MARKET"
    assert reverse_map_order_type("LIMIT") == "LIMIT"
    assert reverse_map_order_type("STOP_LIMIT") == "SL"
    assert reverse_map_order_type("STOP_MARKET") == "SL-M"


def test_price_formatting():
    """Test price precision formatting."""
    # BTC - 2 decimals
    price = format_crypto_price(50000.12345, "BTCUSDT")
    assert price == 50000.12
    
    # ETH - 2 decimals
    price = format_crypto_price(3000.456, "ETHUSDT")
    assert price == 3000.46


def test_quantity_formatting():
    """Test quantity precision formatting."""
    # BTC - 3 decimals
    qty = format_crypto_quantity(0.12345, "BTCUSDT")
    assert qty == 0.123
    
    # ETH - 2 decimals
    qty = format_crypto_quantity(1.456, "ETHUSDT")
    assert qty == 1.46
```

#### Master Contract Tests
**File:** `test/test_pi42_master_contract.py`

```python
import pytest
from broker.pi42.database.master_contract_db import (
    get_contract_info,
    validate_order_params,
    search_contracts
)

def test_get_contract_info():
    """Test contract info retrieval."""
    contract = get_contract_info("BTCUSDT")
    
    assert contract is not None
    assert contract.symbol == "BTCUSDT"
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
    assert "minimum" in result["error"].lower()
    
    # Invalid notional
    result = validate_order_params("BTCUSDT", 0.0001, 1)
    assert result["valid"] == False
    assert "notional" in result["error"].lower()


def test_search_contracts():
    """Test contract search."""
    contracts = search_contracts("BTC")
    
    assert len(contracts) > 0
    assert all("BTC" in c.symbol for c in contracts)
```

### Frontend Unit Tests

#### Component Tests
**File:** `frontend/src/components/crypto/__tests__/LeverageSlider.test.tsx`

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { LeverageSlider } from '../LeverageSlider';

describe('LeverageSlider', () => {
  it('renders with correct initial value', () => {
    render(<LeverageSlider value={10} onChange={() => {}} />);
    expect(screen.getByText('10x')).toBeInTheDocument();
  });

  it('calls onChange when slider moves', () => {
    const onChange = vi.fn();
    render(<LeverageSlider value={10} onChange={onChange} maxLeverage={25} />);
    
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: 15 } });
    
    expect(onChange).toHaveBeenCalledWith(15);
  });

  it('calculates liquidation price correctly', () => {
    render(
      <LeverageSlider
        value={10}
        onChange={() => {}}
        entryPrice={50000}
        quantity={0.5}
        side="LONG"
      />
    );
    
    // Should display liquidation price
    expect(screen.getByText(/Liquidation Price/i)).toBeInTheDocument();
  });

  it('shows risk warning for high leverage', () => {
    render(<LeverageSlider value={20} onChange={() => {}} />);
    expect(screen.getByText(/High leverage increases liquidation risk/i)).toBeInTheDocument();
  });
});
```

**File:** `frontend/src/components/crypto/__tests__/CryptoPositionCard.test.tsx`

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CryptoPositionCard } from '../CryptoPositionCard';

describe('CryptoPositionCard', () => {
  const mockPosition = {
    symbol: 'BTCUSDT',
    side: 'LONG' as const,
    quantity: 0.5,
    entryPrice: 50000,
    markPrice: 51000,
    liquidationPrice: 45000,
    unrealizedPnl: 500,
    margin: 2500,
    leverage: 10,
    marginMode: 'ISOLATED',
    roe: 20
  };

  it('renders position details correctly', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('LONG')).toBeInTheDocument();
    expect(screen.getByText('10x')).toBeInTheDocument();
  });

  it('displays unrealized PnL with correct color', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    
    const pnlElement = screen.getByText(/\$500/);
    expect(pnlElement).toHaveClass('text-green-600');
  });

  it('shows liquidation warning for high risk', () => {
    const highRiskPosition = {
      ...mockPosition,
      markPrice: 46000,
      liquidationPrice: 45000
    };
    
    render(<CryptoPositionCard position={highRiskPosition} />);
    expect(screen.getByText(/Risk: HIGH/i)).toBeInTheDocument();
  });
});
```

## 2. Integration Tests

### API Integration Tests
**File:** `test/integration/test_pi42_api_integration.py`

```python
import pytest
import time
from flask import Flask

@pytest.fixture
def app():
    """Create test Flask app."""
    from app import app
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_api_key():
    """Get test API key."""
    # Create test user and return API key
    return "test_api_key"


class TestPi42Integration:
    """Integration tests for Pi42 API."""
    
    def test_complete_order_flow(self, client, test_api_key):
        """Test complete order placement flow."""
        # 1. Place order
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
        data = response.json
        assert data['status'] == 'success'
        orderid = data['orderid']
        
        # 2. Check order book
        time.sleep(1)
        response = client.get(f'/api/v1/orderbook?apikey={test_api_key}')
        assert response.status_code == 200
        
        # 3. Check positions
        response = client.get(f'/api/v1/positionbook?apikey={test_api_key}')
        assert response.status_code == 200
        positions = response.json['data']
        assert len(positions) > 0
        
        # 4. Close position
        response = client.post('/api/v1/closeposition', json={
            'apikey': test_api_key,
            'symbol': 'BTCUSDT'
        })
        assert response.status_code == 200
    
    def test_leverage_management_flow(self, client, test_api_key):
        """Test leverage management."""
        # Set leverage
        response = client.post('/api/v1/setleverage', json={
            'apikey': test_api_key,
            'symbol': 'BTCUSDT',
            'leverage': 10
        })
        
        assert response.status_code == 200
        assert response.json['status'] == 'success'
    
    def test_margin_management_flow(self, client, test_api_key):
        """Test margin add/reduce."""
        # Add margin
        response = client.post('/api/v1/addmargin', json={
            'apikey': test_api_key,
            'symbol': 'BTCUSDT',
            'amount': 100,
            'margin_asset': 'USDT'
        })
        
        assert response.status_code == 200
        
        # Reduce margin
        response = client.post('/api/v1/reducemargin', json={
            'apikey': test_api_key,
            'symbol': 'BTCUSDT',
            'amount': 50
        })
        
        assert response.status_code == 200
```

### WebSocket Integration Tests
**File:** `test/integration/test_pi42_websocket.py`

```python
import pytest
import asyncio
from broker.pi42.streaming.pi42_adapter import Pi42WebSocketAdapter

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection."""
    adapter = Pi42WebSocketAdapter(test_auth_token)
    
    await adapter.connect()
    assert adapter.is_connected == True
    assert adapter.listen_key is not None
    
    await adapter.disconnect()
    assert adapter.is_connected == False


@pytest.mark.asyncio
async def test_order_update_stream():
    """Test order update streaming."""
    adapter = Pi42WebSocketAdapter(test_auth_token)
    
    received_updates = []
    
    def callback(data):
        received_updates.append(data)
    
    adapter.register_callback("order_update", callback)
    await adapter.connect()
    
    # Place order to trigger update
    # ... place order via API ...
    
    # Wait for update
    await asyncio.sleep(5)
    
    assert len(received_updates) > 0
    assert received_updates[0]['symbol'] == 'BTCUSDT'
    
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_position_update_stream():
    """Test position update streaming."""
    adapter = Pi42WebSocketAdapter(test_auth_token)
    
    received_updates = []
    adapter.register_callback("position_update", lambda d: received_updates.append(d))
    
    await adapter.connect()
    await asyncio.sleep(10)
    
    # Should receive position updates
    assert len(received_updates) > 0
    
    await adapter.disconnect()
```

## 3. End-to-End Tests

### Playwright E2E Tests
**File:** `frontend/e2e/crypto-trading.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Crypto Trading Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5000/react');
    // Login
    await page.fill('[name="username"]', 'testuser');
    await page.fill('[name="password"]', 'testpass');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
  });

  test('complete order placement flow', async ({ page }) => {
    // Navigate to order form
    await page.click('text=Place Order');
    
    // Fill order form
    await page.fill('[name="symbol"]', 'BTCUSDT');
    await page.selectOption('[name="action"]', 'BUY');
    await page.fill('[name="quantity"]', '0.001');
    await page.selectOption('[name="pricetype"]', 'MARKET');
    
    // Set leverage
    await page.locator('[role="slider"]').fill('10');
    
    // Select margin mode
    await page.click('text=Isolated');
    
    // Submit order
    await page.click('button:has-text("Place Order")');
    
    // Verify success
    await expect(page.locator('text=Order placed successfully')).toBeVisible();
    
    // Check position book
    await page.click('text=Positions');
    await expect(page.locator('text=BTCUSDT')).toBeVisible();
    await expect(page.locator('text=LONG')).toBeVisible();
  });

  test('leverage adjustment', async ({ page }) => {
    await page.click('text=Positions');
    
    // Find position card
    const positionCard = page.locator('[data-testid="position-card-BTCUSDT"]');
    
    // Click leverage settings
    await positionCard.locator('text=10x').click();
    
    // Adjust leverage
    await page.locator('[role="slider"]').fill('15');
    await page.click('button:has-text("Update Leverage")');
    
    // Verify update
    await expect(positionCard.locator('text=15x')).toBeVisible();
  });

  test('margin management', async ({ page }) => {
    await page.click('text=Positions');
    
    const positionCard = page.locator('[data-testid="position-card-BTCUSDT"]');
    
    // Add margin
    await positionCard.locator('button:has-text("Add Margin")').click();
    await page.fill('[name="amount"]', '100');
    await page.click('button:has-text("Confirm")');
    
    // Verify success
    await expect(page.locator('text=Margin added successfully')).toBeVisible();
  });

  test('liquidation warning display', async ({ page }) => {
    await page.click('text=Positions');
    
    // Should show liquidation price
    await expect(page.locator('text=Liquidation Price')).toBeVisible();
    
    // Should show risk level
    await expect(page.locator('text=/Risk: (LOW|MEDIUM|HIGH)/i')).toBeVisible();
  });
});
```

## 4. Load Testing

### Locust Load Tests
**File:** `test/load/locustfile.py`

```python
from locust import HttpUser, task, between

class Pi42TradingUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup - get API key."""
        self.api_key = "test_api_key"
    
    @task(3)
    def get_quotes(self):
        """Get quotes - high frequency."""
        self.client.get(
            f"/api/v1/quotes?apikey={self.api_key}&symbol=BTCUSDT&exchange=PI42"
        )
    
    @task(2)
    def get_positions(self):
        """Get positions."""
        self.client.get(f"/api/v1/positionbook?apikey={self.api_key}")
    
    @task(1)
    def place_order(self):
        """Place order - lower frequency."""
        self.client.post("/api/v1/placeorder", json={
            "apikey": self.api_key,
            "symbol": "BTCUSDT",
            "action": "BUY",
            "quantity": "0.001",
            "pricetype": "MARKET",
            "leverage": 5
        })
    
    @task(1)
    def get_funding_rate(self):
        """Get funding rate."""
        self.client.get(
            f"/api/v1/fundingrate?apikey={self.api_key}&symbol=BTCUSDT"
        )
```

Run load tests:
```bash
locust -f test/load/locustfile.py --host=http://localhost:5000
```

## 5. User Acceptance Testing

### UAT Test Cases

#### TC001: Place Market Order
**Preconditions:** User logged in, has USDT balance
**Steps:**
1. Navigate to Order Form
2. Select BTCUSDT
3. Select BUY action
4. Enter quantity 0.01
5. Select MARKET order type
6. Set leverage to 10x
7. Select ISOLATED margin mode
8. Click Place Order

**Expected:** Order placed successfully, position appears in position book

#### TC002: Set Stop Loss
**Preconditions:** User has open LONG position in BTCUSDT
**Steps:**
1. Navigate to Positions
2. Click on BTCUSDT position
3. Click "Set Stop Loss"
4. Enter stop price
5. Confirm

**Expected:** Stop loss order created, visible in order book

#### TC003: Add Margin to Position
**Preconditions:** User has open position with ISOLATED margin
**Steps:**
1. Navigate to Positions
2. Click "Add Margin" on position
3. Enter amount 100 USDT
4. Confirm

**Expected:** Margin added, liquidation price updated

#### TC004: Monitor Funding Fee
**Preconditions:** User has open position
**Steps:**
1. Wait for funding time (every 8 hours)
2. Check position details

**Expected:** Funding fee deducted/credited, notification received

## 6. Test Data Management

### Test Fixtures
**File:** `test/fixtures/crypto_test_data.py`

```python
SAMPLE_CONTRACTS = [
    {
        "symbol": "BTCUSDT",
        "base_asset": "BTC",
        "quote_asset": "USDT",
        "min_quantity": 0.001,
        "max_quantity": 1000,
        "max_leverage": 25
    },
    {
        "symbol": "ETHUSDT",
        "base_asset": "ETH",
        "quote_asset": "USDT",
        "min_quantity": 0.01,
        "max_quantity": 10000,
        "max_leverage": 20
    }
]

SAMPLE_POSITIONS = [
    {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "quantity": 0.5,
        "entry_price": 50000,
        "mark_price": 51000,
        "leverage": 10
    }
]
```

## 7. Continuous Integration

### GitHub Actions Workflow
**File:** `.github/workflows/pi42-tests.yml`

```yaml
name: Pi42 Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      
      - name: Run unit tests
        run: |
          uv run pytest test/test_pi42_*.py -v
      
      - name: Run integration tests
        run: |
          uv run pytest test/integration/test_pi42_*.py -v
      
      - name: Frontend tests
        run: |
          cd frontend
          npm install
          npm run test:run
      
      - name: E2E tests
        run: |
          cd frontend
          npm run e2e
```

## Test Coverage Goals

- **Unit Tests:** > 80% code coverage
- **Integration Tests:** All API endpoints covered
- **E2E Tests:** All critical user flows covered
- **Load Tests:** Handle 100+ concurrent users

## Next Steps

1. Implement all unit tests
2. Create integration test suite
3. Write E2E tests with Playwright
4. Set up load testing with Locust
5. Create UAT test cases
6. Configure CI/CD pipeline
7. Document testing procedures
