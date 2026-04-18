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
            Tuple of (headers, signed_body_or_params)
        """
        timestamp = str(int(time.time() * 1000))

        if method == "GET":
            # For GET requests, sign query string
            if params is None:
                params = {}
            params['timestamp'] = timestamp

            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(query_string)

            headers = {
                'api-key': self.api_key,
                'signature': signature
            }

            return headers, params

        else:  # POST, PUT, DELETE
            # For POST/PUT/DELETE, sign JSON body
            if body is None:
                body = {}
            body['timestamp'] = timestamp

            import json
            json_body = json.dumps(body, separators=(',', ':'))
            signature = self.generate_signature(json_body)

            headers = {
                'api-key': self.api_key,
                'signature': signature,
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
    from utils.encryption import decrypt_token

    decrypted = decrypt_token(auth_token)
    api_key, api_secret = decrypted.split('|')

    return Pi42Auth(api_key, api_secret)
