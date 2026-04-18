# Pi42 Authentication Implementation Plan

## Overview

Pi42 uses HMAC-SHA256 signature-based authentication, which is different from the OAuth2/TOTP methods used by existing stock brokers. This document details the authentication implementation.

## Authentication Flow

### 1. API Key Generation (User Action)
1. User logs into Pi42 web platform
2. Navigates to API Management section
3. Creates API key pair (key + secret)
4. **Secret shown only once** - must be saved immediately
5. User configures in OpenAlgo settings

### 2. Signature Generation

**Algorithm: HMAC-SHA256**

```python
import hmac
import hashlib
import time

def generate_signature(data: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for Pi42 API.
    
    Args:
        data: Query string (GET) or JSON body (POST/PUT/DELETE)
        secret: API secret key
        
    Returns:
        Hex-encoded signature string
    """
    signature = hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature
```

### 3. Request Signing

#### GET Requests
```python
# Example: GET /v1/order/open-orders
timestamp = int(time.time() * 1000)
query_params = f"timestamp={timestamp}"
signature = generate_signature(query_params, api_secret)

headers = {
    "api-key": api_key,
    "signature": signature
}

url = f"https://fapi.pi42.com/v1/order/open-orders?{query_params}"
response = requests.get(url, headers=headers)
```

#### POST/PUT/DELETE Requests
```python
# Example: POST /v1/order/place-order
timestamp = int(time.time() * 1000)
payload = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": 0.5,
    "price": 50000,
    "timestamp": timestamp
}

# Sign the JSON body
json_body = json.dumps(payload)
signature = generate_signature(json_body, api_secret)

headers = {
    "api-key": api_key,
    "signature": signature,
    "Content-Type": "application/json"
}

response = requests.post(
    "https://fapi.pi42.com/v1/order/place-order",
    headers=headers,
    data=json_body
)
```

## Implementation Structure

### File: `broker/pi42/api/auth_api.py`

```python
"""
Pi42 Authentication Module

Handles HMAC-SHA256 signature generation and API key management.
"""

import hashlib
import hmac
import json
import time
from typing import Optional, Tuple

from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)


class Pi42Auth:
    """Pi42 authentication handler."""
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Pi42 authentication.
        
        Args:
            api_key: Pi42 API key
            api_secret: Pi42 API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.pi42.com"
        
    def generate_signature(self, data: str) -> str:
        """
        Generate HMAC-SHA256 signature.
        
        Args:
            data: Data to sign (query string or JSON body)
            
        Returns:
            Hex-encoded signature
        """
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"Generated signature for data: {data[:50]}...")
        return signature
    
    def get_timestamp(self) -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)
    
    def sign_request(self, method: str, endpoint: str, 
                     params: Optional[dict] = None,
                     body: Optional[dict] = None) -> dict:
        """
        Sign API request and return headers.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: Query parameters (for GET)
            body: Request body (for POST/PUT/DELETE)
            
        Returns:
            Dictionary with signed headers
        """
        timestamp = self.get_timestamp()
        
        if method == "GET":
            # Sign query string
            if params is None:
                params = {}
            params['timestamp'] = timestamp
            
            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(query_string)
            
            headers = {
                "api-key": self.api_key,
                "signature": signature
            }
            
            return headers, params
            
        else:  # POST, PUT, DELETE
            # Sign JSON body
            if body is None:
                body = {}
            body['timestamp'] = timestamp
            
            json_body = json.dumps(body, separators=(',', ':'))
            signature = self.generate_signature(json_body)
            
            headers = {
                "api-key": self.api_key,
                "signature": signature,
                "Content-Type": "application/json"
            }
            
            return headers, body


def authenticate_broker(api_key: str, api_secret: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Authenticate with Pi42 and validate credentials.
    
    Args:
        api_key: Pi42 API key
        api_secret: Pi42 API secret
        
    Returns:
        Tuple of (auth_string, error_message)
        auth_string format: "api_key:::api_secret:::base_url"
    """
    try:
        logger.info("Starting Pi42 authentication validation")
        
        if not api_key or not api_secret:
            return None, "API key and secret are required"
        
        # Create auth instance
        auth = Pi42Auth(api_key, api_secret)
        
        # Test authentication by fetching account balance
        client = get_httpx_client()
        
        headers, params = auth.sign_request("GET", "/v1/wallet/futures-wallet/details")
        
        url = f"{auth.base_url}/v1/wallet/futures-wallet/details"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"
        
        logger.debug(f"Testing authentication with URL: {url}")
        
        response = client.get(url, headers=headers, timeout=10)
        
        logger.debug(f"Auth test response status: {response.status_code}")
        logger.debug(f"Auth test response: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            
            if response_data.get("success"):
                logger.info("Pi42 authentication successful")
                
                # Create auth string: api_key:::api_secret:::base_url
                auth_string = f"{api_key}:::{api_secret}:::https://fapi.pi42.com"
                
                return auth_string, None
            else:
                error_msg = response_data.get("message", "Authentication failed")
                logger.error(f"Pi42 auth failed: {error_msg}")
                return None, f"Authentication failed: {error_msg}"
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"Pi42 auth request failed: {error_msg}")
            return None, f"Authentication request failed: {error_msg}"
            
    except Exception as e:
        logger.error(f"Pi42 authentication error: {str(e)}")
        return None, f"Authentication error: {str(e)}"


def get_auth_components(auth_token: str) -> Tuple[str, str, str]:
    """
    Extract components from auth token.
    
    Args:
        auth_token: Auth token string
        
    Returns:
        Tuple of (api_key, api_secret, base_url)
    """
    try:
        api_key, api_secret, base_url = auth_token.split(":::")
        return api_key, api_secret, base_url
    except ValueError:
        logger.error("Invalid auth token format")
        raise ValueError("Invalid auth token format")


def create_auth_instance(auth_token: str) -> Pi42Auth:
    """
    Create Pi42Auth instance from auth token.
    
    Args:
        auth_token: Auth token string
        
    Returns:
        Pi42Auth instance
    """
    api_key, api_secret, _ = get_auth_components(auth_token)
    return Pi42Auth(api_key, api_secret)
```

## WebSocket Authentication

Pi42 supports two WebSocket authentication methods:

### Method 1: Listen Key (Recommended)

```python
def create_listen_key(auth_token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Create listen key for WebSocket authentication.
    
    Returns:
        Tuple of (listen_key, error_message)
    """
    try:
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        headers, body = auth.sign_request("POST", "/v1/retail/listen-key")
        
        response = client.post(
            f"{auth.base_url}/v1/retail/listen-key",
            headers=headers,
            json=body
        )
        
        if response.status_code == 200:
            data = response.json()
            listen_key = data.get("listenKey")
            logger.info("Listen key created successfully")
            return listen_key, None
        else:
            error_msg = f"Failed to create listen key: {response.text}"
            logger.error(error_msg)
            return None, error_msg
            
    except Exception as e:
        logger.error(f"Error creating listen key: {str(e)}")
        return None, str(e)


def update_listen_key(auth_token: str, listen_key: str) -> bool:
    """
    Update listen key to keep it alive (call every 30 minutes).
    
    Returns:
        True if successful, False otherwise
    """
    try:
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        headers, body = auth.sign_request("PUT", "/v1/retail/listen-key", 
                                          body={"listenKey": listen_key})
        
        response = client.put(
            f"{auth.base_url}/v1/retail/listen-key",
            headers=headers,
            json=body
        )
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error updating listen key: {str(e)}")
        return False


def delete_listen_key(auth_token: str, listen_key: str) -> bool:
    """
    Delete listen key when done.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        auth = create_auth_instance(auth_token)
        client = get_httpx_client()
        
        headers, body = auth.sign_request("DELETE", "/v1/retail/listen-key",
                                          body={"listenKey": listen_key})
        
        response = client.delete(
            f"{auth.base_url}/v1/retail/listen-key",
            headers=headers,
            json=body
        )
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error deleting listen key: {str(e)}")
        return False
```

### Method 2: Direct Signature (Alternative)

```python
def get_websocket_auth_params(auth_token: str) -> dict:
    """
    Get WebSocket authentication parameters using signature method.
    
    Returns:
        Dictionary with api-key and signature
    """
    auth = create_auth_instance(auth_token)
    timestamp = auth.get_timestamp()
    
    # Sign timestamp for WebSocket auth
    signature = auth.generate_signature(str(timestamp))
    
    return {
        "api-key": auth.api_key,
        "signature": signature,
        "timestamp": timestamp
    }
```

## Rate Limiting

Pi42 has strict rate limits that must be respected:

```python
class RateLimiter:
    """Rate limiter for Pi42 API."""
    
    def __init__(self):
        self.limits = {
            "place_order": {"limit": 20, "window": 1},      # 20/second
            "delete_order": {"limit": 30, "window": 60},    # 30/minute
            "default": {"limit": 60, "window": 60}          # 60/minute
        }
        self.requests = {}
    
    def check_limit(self, endpoint_type: str = "default") -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            endpoint_type: Type of endpoint (place_order, delete_order, default)
            
        Returns:
            True if within limit, False otherwise
        """
        now = time.time()
        limit_config = self.limits.get(endpoint_type, self.limits["default"])
        
        if endpoint_type not in self.requests:
            self.requests[endpoint_type] = []
        
        # Remove old requests outside window
        window_start = now - limit_config["window"]
        self.requests[endpoint_type] = [
            req_time for req_time in self.requests[endpoint_type]
            if req_time > window_start
        ]
        
        # Check if within limit
        if len(self.requests[endpoint_type]) < limit_config["limit"]:
            self.requests[endpoint_type].append(now)
            return True
        
        return False
    
    def wait_if_needed(self, endpoint_type: str = "default"):
        """Wait if rate limit would be exceeded."""
        while not self.check_limit(endpoint_type):
            time.sleep(0.1)
```

## Error Handling

```python
class Pi42AuthError(Exception):
    """Pi42 authentication error."""
    pass


class Pi42RateLimitError(Exception):
    """Pi42 rate limit exceeded."""
    pass


def handle_auth_error(response):
    """
    Handle authentication errors from Pi42 API.
    
    Args:
        response: HTTP response object
        
    Raises:
        Pi42AuthError: If authentication failed
    """
    if response.status_code == 401:
        raise Pi42AuthError("Invalid API key or signature")
    elif response.status_code == 403:
        raise Pi42AuthError("API key does not have required permissions")
    elif response.status_code == 429:
        raise Pi42RateLimitError("Rate limit exceeded")
```

## Testing

```python
def test_authentication():
    """Test Pi42 authentication."""
    # Test with valid credentials
    auth_token, error = authenticate_broker("test_key", "test_secret")
    assert error is None or "Authentication" in error
    
    # Test with invalid credentials
    auth_token, error = authenticate_broker("invalid", "invalid")
    assert error is not None
    
    # Test signature generation
    auth = Pi42Auth("test_key", "test_secret")
    signature = auth.generate_signature("test_data")
    assert len(signature) == 64  # SHA256 hex is 64 chars
    
    # Test timestamp
    timestamp = auth.get_timestamp()
    assert timestamp > 0
    assert len(str(timestamp)) == 13  # Milliseconds
```

## Configuration

Add to `.env`:

```bash
# Pi42 Configuration
PI42_API_KEY=your_api_key_here
PI42_API_SECRET=your_api_secret_here
PI42_BASE_URL=https://fapi.pi42.com
PI42_WS_URL=wss://fawss-uds.pi42.com/auth-stream
```

## Security Considerations

1. **Secret Storage**: API secret must be encrypted in database
2. **Signature Validation**: Always validate signature before sending
3. **Timestamp Sync**: Ensure server time is synchronized (NTP)
4. **Rate Limiting**: Implement client-side rate limiting
5. **Error Logging**: Never log API secret in logs
6. **Key Rotation**: Support API key rotation without downtime

## Next Steps

1. Implement `auth_api.py` with all functions
2. Add rate limiter class
3. Implement WebSocket authentication
4. Add unit tests for signature generation
5. Test with Pi42 sandbox/testnet
6. Document API key generation process for users
