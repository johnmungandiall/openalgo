"""Pi42 market data API."""

import requests
from typing import Dict, Optional
from broker.pi42.api.auth_api import create_auth_instance


class BrokerData:
    """Pi42 market data handler."""

    def __init__(self, auth_token: str):
        """Initialize with auth token."""
        self.auth = create_auth_instance(auth_token)

    def get_quotes(self, symbol: str) -> Dict:
        """
        Get quote data for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Quote data dictionary
        """
        endpoint = '/v1/ticker/24hr'
        params = {'symbol': symbol}
        headers, _ = self.auth.sign_request('GET', endpoint, params=params)

        url = f"{self.auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to get quotes: {response.text}")

        data = response.json()

        return {
            'symbol': data['symbol'],
            'exchange': 'PI42',
            'ltp': float(data['lastPrice']),
            'open': float(data['openPrice']),
            'high': float(data['highPrice']),
            'low': float(data['lowPrice']),
            'close': float(data['lastPrice']),
            'volume': float(data['volume']),
            'oi': float(data.get('openInterest', 0)),
            'mark_price': float(data.get('markPrice', data['lastPrice'])),
            'index_price': float(data.get('indexPrice', data['lastPrice'])),
            'funding_rate': float(data.get('lastFundingRate', 0))
        }

    def get_depth(self, symbol: str) -> Dict:
        """
        Get order book depth.

        Args:
            symbol: Trading symbol

        Returns:
            Depth data dictionary
        """
        endpoint = '/v1/depth'
        params = {'symbol': symbol, 'limit': 5}
        headers, _ = self.auth.sign_request('GET', endpoint, params=params)

        url = f"{self.auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to get depth: {response.text}")

        data = response.json()

        return {
            'symbol': symbol,
            'exchange': 'PI42',
            'bids': [[float(p), float(q)] for p, q in data['bids']],
            'asks': [[float(p), float(q)] for p, q in data['asks']]
        }

    def get_history(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> list:
        """
        Get historical klines data.

        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d)
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
            limit: Number of klines

        Returns:
            List of kline data
        """
        endpoint = '/v1/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }

        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        headers, _ = self.auth.sign_request('GET', endpoint, params=params)

        url = f"{self.auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to get history: {response.text}")

        return response.json()
