"""Pi42 broker adapter for OpenAlgo WebSocket proxy."""

import json
from typing import Dict, Optional
from broker.pi42.streaming.websocket_client import create_websocket_client
from broker.pi42.streaming.market_data_stream import Pi42MarketDataStream
from broker.pi42.streaming.user_data_stream import Pi42UserDataStream


class Pi42BrokerAdapter:
    """
    Pi42 broker adapter for OpenAlgo WebSocket proxy.

    Integrates Pi42 WebSocket streams with OpenAlgo's unified WebSocket proxy.
    """

    def __init__(self, auth_token: str, zmq_publisher=None):
        """
        Initialize broker adapter.

        Args:
            auth_token: Encrypted auth token
            zmq_publisher: ZeroMQ publisher for message distribution
        """
        self.auth_token = auth_token
        self.zmq_publisher = zmq_publisher
        self.ws_client = None
        self.market_stream = None
        self.user_stream = None
        self.active_subscriptions = {}

    def connect(self):
        """Establish WebSocket connection."""
        self.ws_client = create_websocket_client(self.auth_token)
        self.ws_client.connect()

        self.market_stream = Pi42MarketDataStream(self.ws_client)
        self.user_stream = Pi42UserDataStream(self.ws_client)

    def disconnect(self):
        """Close WebSocket connection."""
        if self.ws_client:
            self.ws_client.disconnect()

    def subscribe_ticker(self, symbol: str):
        """
        Subscribe to ticker updates.

        Args:
            symbol: Trading symbol
        """
        def callback(data: Dict):
            self._publish_message('ticker', symbol, data)

        self.market_stream.subscribe_ticker(symbol, callback)
        self.active_subscriptions[f"ticker:{symbol}"] = True

    def subscribe_depth(self, symbol: str, levels: int = 5):
        """
        Subscribe to order book depth.

        Args:
            symbol: Trading symbol
            levels: Depth levels
        """
        def callback(data: Dict):
            self._publish_message('depth', symbol, data)

        self.market_stream.subscribe_depth(symbol, callback, levels)
        self.active_subscriptions[f"depth:{symbol}"] = True

    def subscribe_trades(self, symbol: str):
        """
        Subscribe to recent trades.

        Args:
            symbol: Trading symbol
        """
        def callback(data: Dict):
            self._publish_message('trades', symbol, data)

        self.market_stream.subscribe_trades(symbol, callback)
        self.active_subscriptions[f"trades:{symbol}"] = True

    def subscribe_orders(self):
        """Subscribe to order updates."""
        def callback(data: Dict):
            if data['event_type'] == 'order':
                self._publish_message('orders', 'all', data)

        self.user_stream.start_user_stream(callback)
        self.active_subscriptions["orders:all"] = True

    def subscribe_positions(self):
        """Subscribe to position updates."""
        def callback(data: Dict):
            if data['event_type'] == 'account':
                # Extract position data
                positions = data.get('positions', [])
                for position in positions:
                    self._publish_message('positions', position['symbol'], position)

        self.user_stream.start_user_stream(callback)
        self.active_subscriptions["positions:all"] = True

    def subscribe_balance(self):
        """Subscribe to balance updates."""
        def callback(data: Dict):
            if data['event_type'] == 'account':
                # Extract balance data
                balances = data.get('balances', [])
                for balance in balances:
                    self._publish_message('balance', balance['asset'], balance)

        self.user_stream.start_user_stream(callback)
        self.active_subscriptions["balance:all"] = True

    def unsubscribe_ticker(self, symbol: str):
        """Unsubscribe from ticker updates."""
        self.market_stream.unsubscribe_ticker(symbol)
        self.active_subscriptions.pop(f"ticker:{symbol}", None)

    def unsubscribe_depth(self, symbol: str, levels: int = 5):
        """Unsubscribe from depth updates."""
        self.market_stream.unsubscribe_depth(symbol, levels)
        self.active_subscriptions.pop(f"depth:{symbol}", None)

    def unsubscribe_trades(self, symbol: str):
        """Unsubscribe from trades."""
        self.market_stream.unsubscribe_trades(symbol)
        self.active_subscriptions.pop(f"trades:{symbol}", None)

    def unsubscribe_orders(self):
        """Unsubscribe from order updates."""
        self.user_stream.stop_user_stream()
        self.active_subscriptions.pop("orders:all", None)

    def _publish_message(self, channel: str, symbol: str, data: Dict):
        """
        Publish message to ZeroMQ.

        Args:
            channel: Channel name
            symbol: Trading symbol
            data: Message data
        """
        if self.zmq_publisher:
            message = {
                'broker': 'pi42',
                'channel': channel,
                'symbol': symbol,
                'data': data
            }

            try:
                self.zmq_publisher.send_string(json.dumps(message))
            except Exception as e:
                print(f"Error publishing message: {e}")

    def get_active_subscriptions(self) -> Dict:
        """
        Get active subscriptions.

        Returns:
            Dictionary of active subscriptions
        """
        return self.active_subscriptions.copy()

    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected.

        Returns:
            Connection status
        """
        return self.ws_client.is_connected if self.ws_client else False

    def is_authenticated(self) -> bool:
        """
        Check if WebSocket is authenticated.

        Returns:
            Authentication status
        """
        return self.ws_client.is_authenticated if self.ws_client else False


def create_broker_adapter(auth_token: str, zmq_publisher=None) -> Pi42BrokerAdapter:
    """
    Create Pi42 broker adapter.

    Args:
        auth_token: Encrypted auth token
        zmq_publisher: ZeroMQ publisher

    Returns:
        Pi42BrokerAdapter instance
    """
    adapter = Pi42BrokerAdapter(auth_token, zmq_publisher)
    adapter.connect()
    return adapter
