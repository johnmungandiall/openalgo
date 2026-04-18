"""Pi42 market data streams."""

from typing import Dict, Callable
from broker.pi42.streaming.websocket_client import Pi42WebSocketClient


class Pi42MarketDataStream:
    """Pi42 market data streaming."""

    def __init__(self, ws_client: Pi42WebSocketClient):
        """
        Initialize market data stream.

        Args:
            ws_client: WebSocket client instance
        """
        self.ws_client = ws_client

    def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Subscribe to 24hr ticker stream.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            callback: Callback function(data: Dict)
        """
        channel = f"ticker@{symbol}"

        def ticker_callback(data: Dict):
            """Process ticker data."""
            processed = {
                'symbol': data.get('s'),
                'event_type': 'ticker',
                'event_time': data.get('E'),
                'price_change': float(data.get('p', 0)),
                'price_change_percent': float(data.get('P', 0)),
                'last_price': float(data.get('c', 0)),
                'open_price': float(data.get('o', 0)),
                'high_price': float(data.get('h', 0)),
                'low_price': float(data.get('l', 0)),
                'volume': float(data.get('v', 0)),
                'quote_volume': float(data.get('q', 0)),
                'open_interest': float(data.get('oi', 0)),
                'mark_price': float(data.get('mp', 0)),
                'index_price': float(data.get('ip', 0)),
                'funding_rate': float(data.get('fr', 0))
            }
            callback(processed)

        self.ws_client.subscribe(channel, ticker_callback)

    def subscribe_depth(self, symbol: str, callback: Callable, levels: int = 5):
        """
        Subscribe to order book depth stream.

        Args:
            symbol: Trading symbol
            callback: Callback function(data: Dict)
            levels: Depth levels (5, 10, 20)
        """
        channel = f"depth{levels}@{symbol}"

        def depth_callback(data: Dict):
            """Process depth data."""
            processed = {
                'symbol': data.get('s'),
                'event_type': 'depth',
                'event_time': data.get('E'),
                'bids': [[float(p), float(q)] for p, q in data.get('b', [])],
                'asks': [[float(p), float(q)] for p, q in data.get('a', [])]
            }
            callback(processed)

        self.ws_client.subscribe(channel, depth_callback)

    def subscribe_trades(self, symbol: str, callback: Callable):
        """
        Subscribe to recent trades stream.

        Args:
            symbol: Trading symbol
            callback: Callback function(data: Dict)
        """
        channel = f"trade@{symbol}"

        def trade_callback(data: Dict):
            """Process trade data."""
            processed = {
                'symbol': data.get('s'),
                'event_type': 'trade',
                'event_time': data.get('E'),
                'trade_id': data.get('t'),
                'price': float(data.get('p', 0)),
                'quantity': float(data.get('q', 0)),
                'buyer_order_id': data.get('b'),
                'seller_order_id': data.get('a'),
                'trade_time': data.get('T'),
                'is_buyer_maker': data.get('m', False)
            }
            callback(processed)

        self.ws_client.subscribe(channel, trade_callback)

    def subscribe_kline(self, symbol: str, interval: str, callback: Callable):
        """
        Subscribe to kline/candlestick stream.

        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d)
            callback: Callback function(data: Dict)
        """
        channel = f"kline_{interval}@{symbol}"

        def kline_callback(data: Dict):
            """Process kline data."""
            k = data.get('k', {})
            processed = {
                'symbol': data.get('s'),
                'event_type': 'kline',
                'event_time': data.get('E'),
                'interval': k.get('i'),
                'open_time': k.get('t'),
                'close_time': k.get('T'),
                'open': float(k.get('o', 0)),
                'high': float(k.get('h', 0)),
                'low': float(k.get('l', 0)),
                'close': float(k.get('c', 0)),
                'volume': float(k.get('v', 0)),
                'is_closed': k.get('x', False)
            }
            callback(processed)

        self.ws_client.subscribe(channel, kline_callback)

    def subscribe_mark_price(self, symbol: str, callback: Callable):
        """
        Subscribe to mark price stream.

        Args:
            symbol: Trading symbol
            callback: Callback function(data: Dict)
        """
        channel = f"markPrice@{symbol}"

        def mark_price_callback(data: Dict):
            """Process mark price data."""
            processed = {
                'symbol': data.get('s'),
                'event_type': 'markPrice',
                'event_time': data.get('E'),
                'mark_price': float(data.get('p', 0)),
                'index_price': float(data.get('i', 0)),
                'funding_rate': float(data.get('r', 0)),
                'next_funding_time': data.get('T')
            }
            callback(processed)

        self.ws_client.subscribe(channel, mark_price_callback)

    def subscribe_liquidation(self, symbol: str, callback: Callable):
        """
        Subscribe to liquidation stream.

        Args:
            symbol: Trading symbol
            callback: Callback function(data: Dict)
        """
        channel = f"forceOrder@{symbol}"

        def liquidation_callback(data: Dict):
            """Process liquidation data."""
            o = data.get('o', {})
            processed = {
                'symbol': o.get('s'),
                'event_type': 'forceOrder',
                'event_time': data.get('E'),
                'side': o.get('S'),
                'order_type': o.get('o'),
                'quantity': float(o.get('q', 0)),
                'price': float(o.get('p', 0)),
                'average_price': float(o.get('ap', 0)),
                'order_status': o.get('X'),
                'time_in_force': o.get('f'),
                'order_id': o.get('i')
            }
            callback(processed)

        self.ws_client.subscribe(channel, liquidation_callback)

    def unsubscribe_ticker(self, symbol: str):
        """Unsubscribe from ticker stream."""
        self.ws_client.unsubscribe(f"ticker@{symbol}")

    def unsubscribe_depth(self, symbol: str, levels: int = 5):
        """Unsubscribe from depth stream."""
        self.ws_client.unsubscribe(f"depth{levels}@{symbol}")

    def unsubscribe_trades(self, symbol: str):
        """Unsubscribe from trades stream."""
        self.ws_client.unsubscribe(f"trade@{symbol}")

    def unsubscribe_kline(self, symbol: str, interval: str):
        """Unsubscribe from kline stream."""
        self.ws_client.unsubscribe(f"kline_{interval}@{symbol}")

    def unsubscribe_mark_price(self, symbol: str):
        """Unsubscribe from mark price stream."""
        self.ws_client.unsubscribe(f"markPrice@{symbol}")

    def unsubscribe_liquidation(self, symbol: str):
        """Unsubscribe from liquidation stream."""
        self.ws_client.unsubscribe(f"forceOrder@{symbol}")
