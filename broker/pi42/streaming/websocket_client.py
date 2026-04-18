"""Pi42 WebSocket client for real-time data streaming."""

import json
import time
import threading
import websocket
from typing import Dict, Callable, Optional, List
from broker.pi42.api.auth_api import Pi42Auth


class Pi42WebSocketClient:
    """Pi42 WebSocket client with authentication and reconnection."""

    def __init__(self, auth: Pi42Auth):
        """
        Initialize WebSocket client.

        Args:
            auth: Pi42Auth instance
        """
        self.auth = auth
        self.ws_url = 'wss://stream.pi42.com/ws'
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_connected = False
        self.is_authenticated = False
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5
        self.heartbeat_interval = 30
        self.last_heartbeat = 0
        self.thread: Optional[threading.Thread] = None
        self.should_run = False

    def connect(self):
        """Establish WebSocket connection."""
        if self.is_connected:
            return

        self.should_run = True
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # Run in separate thread
        self.thread = threading.Thread(target=self._run_forever, daemon=True)
        self.thread.start()

    def _run_forever(self):
        """Run WebSocket connection loop."""
        while self.should_run:
            try:
                self.ws.run_forever()
            except Exception as e:
                print(f"WebSocket error: {e}")

            if self.should_run:
                self._handle_reconnect()

    def disconnect(self):
        """Close WebSocket connection."""
        self.should_run = False
        self.is_connected = False
        self.is_authenticated = False

        if self.ws:
            self.ws.close()

    def _on_open(self, ws):
        """Handle WebSocket connection opened."""
        print("WebSocket connected")
        self.is_connected = True
        self.reconnect_attempts = 0
        self._authenticate()
        self._start_heartbeat()

    def _on_message(self, ws, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get('e')  # Event type

            if msg_type == 'auth':
                self._handle_auth_response(data)
            elif msg_type == 'pong':
                self.last_heartbeat = time.time()
            else:
                self._route_message(data)

        except json.JSONDecodeError:
            print(f"Invalid JSON message: {message}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        print(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed."""
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        self.is_authenticated = False

    def _authenticate(self):
        """Authenticate WebSocket connection."""
        timestamp = str(int(time.time() * 1000))
        auth_string = f"timestamp={timestamp}"
        signature = self.auth.generate_signature(auth_string)

        auth_message = {
            'method': 'auth',
            'params': {
                'apiKey': self.auth.api_key,
                'signature': signature,
                'timestamp': timestamp
            }
        }

        self._send_message(auth_message)

    def _handle_auth_response(self, data: Dict):
        """Handle authentication response."""
        if data.get('status') == 'success':
            print("WebSocket authenticated")
            self.is_authenticated = True
            self._resubscribe_all()
        else:
            print(f"Authentication failed: {data.get('message')}")

    def _start_heartbeat(self):
        """Start heartbeat thread."""
        def heartbeat_loop():
            while self.should_run and self.is_connected:
                if time.time() - self.last_heartbeat > self.heartbeat_interval:
                    self._send_ping()
                time.sleep(10)

        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()

    def _send_ping(self):
        """Send ping message."""
        ping_message = {'method': 'ping'}
        self._send_message(ping_message)

    def _handle_reconnect(self):
        """Handle reconnection logic."""
        if not self.should_run:
            return

        self.reconnect_attempts += 1

        if self.reconnect_attempts > self.max_reconnect_attempts:
            print("Max reconnection attempts reached")
            self.should_run = False
            return

        delay = self.reconnect_delay * self.reconnect_attempts
        print(f"Reconnecting in {delay} seconds (attempt {self.reconnect_attempts})")
        time.sleep(delay)

    def subscribe(self, channel: str, callback: Callable):
        """
        Subscribe to channel.

        Args:
            channel: Channel name (e.g., 'ticker@BTCUSDT')
            callback: Callback function for messages
        """
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []

        self.subscriptions[channel].append(callback)

        if self.is_authenticated:
            self._send_subscribe(channel)

    def unsubscribe(self, channel: str):
        """
        Unsubscribe from channel.

        Args:
            channel: Channel name
        """
        if channel in self.subscriptions:
            del self.subscriptions[channel]

        if self.is_authenticated:
            self._send_unsubscribe(channel)

    def _send_subscribe(self, channel: str):
        """Send subscribe message."""
        subscribe_message = {
            'method': 'subscribe',
            'params': [channel]
        }
        self._send_message(subscribe_message)

    def _send_unsubscribe(self, channel: str):
        """Send unsubscribe message."""
        unsubscribe_message = {
            'method': 'unsubscribe',
            'params': [channel]
        }
        self._send_message(unsubscribe_message)

    def _resubscribe_all(self):
        """Resubscribe to all channels after reconnection."""
        for channel in self.subscriptions.keys():
            self._send_subscribe(channel)

    def _route_message(self, data: Dict):
        """Route message to appropriate callbacks."""
        event_type = data.get('e')
        symbol = data.get('s')

        # Construct channel name
        channel = f"{event_type}@{symbol}" if symbol else event_type

        # Call all callbacks for this channel
        if channel in self.subscriptions:
            for callback in self.subscriptions[channel]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in callback for {channel}: {e}")

    def _send_message(self, message: Dict):
        """Send message to WebSocket."""
        if self.ws and self.is_connected:
            try:
                self.ws.send(json.dumps(message))
            except Exception as e:
                print(f"Error sending message: {e}")


def create_websocket_client(auth_token: str) -> Pi42WebSocketClient:
    """
    Create WebSocket client from auth token.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Pi42WebSocketClient instance
    """
    from broker.pi42.api.auth_api import create_auth_instance

    auth = create_auth_instance(auth_token)
    return Pi42WebSocketClient(auth)
