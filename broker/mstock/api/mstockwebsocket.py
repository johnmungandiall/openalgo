"""
Synchronous mstock WebSocket client using websocket-client library.

Uses sync websocket-client instead of async websockets to avoid asyncio
event loop conflicts with eventlet in gunicorn+eventlet deployments.
"""
import json
import os
import ssl
import struct
import threading
import time
from typing import Any

import websocket

from utils.logging import get_logger

logger = get_logger(__name__)


class MstockWebSocket:
    """
    WebSocket client for mstock broker's market data API.
    Handles binary packet parsing as per mstock WebSocket protocol.
    Supports both one-off fetches and persistent streaming connections.
    """

    WS_URL = "wss://ws.mstock.trade"

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.api_key = os.getenv("BROKER_API_SECRET") or os.getenv("BROKER_API_KEY")
        self.ws_url = f"{self.WS_URL}?API_KEY={self.api_key}&ACCESS_TOKEN={self.auth_token}"

        # Streaming mode variables
        self.ws: websocket.WebSocketApp | None = None
        self.running = False
        self._connected = False
        self.data_callback = None
        self.on_login_callback = None
        self.subscriptions: dict[str, dict] = {}
        self._ws_thread: threading.Thread | None = None
        self._logged_in = False
        self._login_event = threading.Event()
        self._login_lock = threading.Lock()
        # mstock sends no login-acknowledgement frame, so login is confirmed
        # implicitly this many seconds after the socket opens (the same brief
        # settle that fetch_quotes_bulk relies on before subscribing).
        self._login_settle_secs = 0.5

    @staticmethod
    def parse_binary_packet(data: bytes) -> dict | None:
        """
        Parse mstock binary quote packet.
        The packet can be:
        - 51 bytes (LTP mode - mode 1)
        - 123 bytes (Quote mode - mode 2)
        - 379 bytes (Full quote packet - mode 3)
        - 383+ bytes (4 byte header + quote packet)
        """
        try:
            if len(data) == 51:
                quote = {
                    "subscription_mode": data[0],
                    "exchange_type": data[1],
                    "token": data[2:27].decode("utf-8").strip("\x00"),
                    "sequence_number": struct.unpack("<Q", data[27:35])[0],
                    "exchange_timestamp": struct.unpack("<Q", data[35:43])[0],
                    "ltp": struct.unpack("<Q", data[43:51])[0] / 100.0,
                    "last_traded_qty": 0, "avg_price": 0, "volume": 0,
                    "total_buy_qty": 0, "total_sell_qty": 0,
                    "open": 0, "high": 0, "low": 0, "close": 0,
                    "last_traded_timestamp": 0, "oi": 0, "oi_percent": 0,
                    "upper_circuit": 0, "lower_circuit": 0,
                    "week_52_high": 0, "week_52_low": 0,
                    "bids": [], "asks": [],
                }
                return quote

            elif len(data) == 123:
                quote = {
                    "subscription_mode": data[0],
                    "exchange_type": data[1],
                    "token": data[2:27].decode("utf-8").strip("\x00"),
                    "sequence_number": struct.unpack("<Q", data[27:35])[0],
                    "exchange_timestamp": struct.unpack("<Q", data[35:43])[0],
                    "ltp": struct.unpack("<Q", data[43:51])[0] / 100.0,
                    "last_traded_qty": struct.unpack("<Q", data[51:59])[0],
                    "avg_price": struct.unpack("<Q", data[59:67])[0] / 100.0,
                    "volume": struct.unpack("<Q", data[67:75])[0],
                    "total_buy_qty": struct.unpack("<d", data[75:83])[0],
                    "total_sell_qty": struct.unpack("<d", data[83:91])[0],
                    "open": struct.unpack("<Q", data[91:99])[0] / 100.0,
                    "high": struct.unpack("<Q", data[99:107])[0] / 100.0,
                    "low": struct.unpack("<Q", data[107:115])[0] / 100.0,
                    "close": struct.unpack("<Q", data[115:123])[0] / 100.0,
                    "last_traded_timestamp": 0, "oi": 0, "oi_percent": 0,
                    "upper_circuit": 0, "lower_circuit": 0,
                    "week_52_high": 0, "week_52_low": 0,
                    "bids": [], "asks": [],
                }
                return quote

            elif len(data) == 379:
                packet = data
            elif len(data) >= 383:
                num_packets = struct.unpack("<H", data[0:2])[0]
                packet_size = struct.unpack("<H", data[2:4])[0]
                packet = data[4:4 + 379]
            else:
                logger.error(f"Invalid packet size: {len(data)} bytes")
                return None

            # Parse full 379-byte quote packet
            quote = {
                "subscription_mode": packet[0],
                "exchange_type": packet[1],
                "token": packet[2:27].decode("utf-8").strip("\x00"),
                "sequence_number": struct.unpack("<Q", packet[27:35])[0],
                "exchange_timestamp": struct.unpack("<Q", packet[35:43])[0],
                "ltp": struct.unpack("<Q", packet[43:51])[0] / 100.0,
                "last_traded_qty": struct.unpack("<Q", packet[51:59])[0],
                "avg_price": struct.unpack("<Q", packet[59:67])[0] / 100.0,
                "volume": struct.unpack("<Q", packet[67:75])[0],
                "total_buy_qty": struct.unpack("<d", packet[75:83])[0],
                "total_sell_qty": struct.unpack("<d", packet[83:91])[0],
                "open": struct.unpack("<Q", packet[91:99])[0] / 100.0,
                "high": struct.unpack("<Q", packet[99:107])[0] / 100.0,
                "low": struct.unpack("<Q", packet[107:115])[0] / 100.0,
                "close": struct.unpack("<Q", packet[115:123])[0] / 100.0,
                "last_traded_timestamp": struct.unpack("<Q", packet[123:131])[0],
                "oi": struct.unpack("<Q", packet[131:139])[0],
                "oi_percent": struct.unpack("<Q", packet[139:147])[0] / 100.0,
                "upper_circuit": struct.unpack("<Q", packet[347:355])[0] / 100.0,
                "lower_circuit": struct.unpack("<Q", packet[355:363])[0] / 100.0,
                "week_52_high": struct.unpack("<Q", packet[363:371])[0] / 100.0,
                "week_52_low": struct.unpack("<Q", packet[371:379])[0] / 100.0,
            }

            # Parse market depth (bytes 147-347)
            depth_data = packet[147:347]
            quote["bids"] = []
            quote["asks"] = []

            for i in range(5):
                bid_offset = i * 20
                try:
                    qty = struct.unpack("<Q", depth_data[bid_offset + 2:bid_offset + 10])[0]
                    price = struct.unpack("<Q", depth_data[bid_offset + 10:bid_offset + 18])[0] / 100.0
                    num_orders = struct.unpack("<H", depth_data[bid_offset + 18:bid_offset + 20])[0]
                    quote["bids"].append({"price": price, "quantity": qty, "orders": num_orders})
                except Exception:
                    quote["bids"].append({"price": 0, "quantity": 0, "orders": 0})

            for i in range(5):
                ask_offset = 100 + (i * 20)
                try:
                    qty = struct.unpack("<Q", depth_data[ask_offset + 2:ask_offset + 10])[0]
                    price = struct.unpack("<Q", depth_data[ask_offset + 10:ask_offset + 18])[0] / 100.0
                    num_orders = struct.unpack("<H", depth_data[ask_offset + 18:ask_offset + 20])[0]
                    quote["asks"].append({"price": price, "quantity": qty, "orders": num_orders})
                except Exception:
                    quote["asks"].append({"price": 0, "quantity": 0, "orders": 0})

            return quote

        except Exception as e:
            logger.error(f"Error parsing binary packet: {str(e)}")
            return None

    # ==================== Streaming Mode Methods ====================

    def connect_stream(self, data_callback, on_login=None):
        """
        Start persistent WebSocket connection for streaming data.
        Returns immediately — connection happens in background thread.

        Args:
            data_callback: Callback function(quote_data) called when data is received
            on_login: Optional callback invoked (no args) once login is confirmed,
                on the initial connection and after every reconnect. Lets the
                caller flush subscriptions that were requested before the socket
                finished its LOGIN handshake. When provided it replaces the
                built-in _resubscribe_all() so subscriptions are not sent twice.
        """
        self.data_callback = data_callback
        self.on_login_callback = on_login
        self.running = True
        self._logged_in = False
        self._login_event.clear()

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
        )

        self._ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._ws_thread.start()
        logger.info("mstock WebSocket connection thread started")

    def _run_websocket(self):
        """Run the WebSocket connection with reconnection"""
        self._reconnect_attempts = 0
        max_attempts = 10

        while self.running:
            try:
                self.ws.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_NONE},
                    ping_interval=20,
                    ping_timeout=10,
                )
            except Exception as e:
                logger.error(f"WebSocket run_forever error: {e}")

            self._connected = False
            self._logged_in = False

            if not self.running:
                break

            self._reconnect_attempts += 1
            if self._reconnect_attempts >= max_attempts:
                logger.error("Max reconnect attempts reached")
                break

            delay = min(2 * (1.5 ** self._reconnect_attempts), 60)
            logger.info(f"Reconnecting in {delay:.0f}s (attempt {self._reconnect_attempts})...")
            time.sleep(delay)

            # Recreate WebSocketApp for reconnection
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_ws_open,
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
            )

    def _on_ws_open(self, ws):
        """Called when WebSocket connection is opened"""
        logger.info("mstock WebSocket connected")
        self._connected = True
        self._reconnect_attempts = 0

        # Send LOGIN message
        login_msg = f"LOGIN:{self.auth_token}"
        ws.send(login_msg)
        logger.debug("Sent LOGIN message")

        # mstock does not send a login-acknowledgement frame, so confirm login
        # implicitly after a brief settle (a string ack, if one ever arrives,
        # confirms it sooner via _on_ws_message). Done off-thread so the open
        # handler does not block the reader.
        threading.Thread(target=self._post_login_settle, daemon=True).start()

    def _post_login_settle(self):
        """Confirm login implicitly once the socket has had time to settle."""
        time.sleep(self._login_settle_secs)
        if self.running and self._connected:
            self._confirm_login()

    def _confirm_login(self):
        """Mark the session logged in and flush subscriptions exactly once.

        Idempotent and thread-safe: invoked from both the post-login settle
        timer and the string-message handler, whichever fires first.
        """
        with self._login_lock:
            if self._logged_in:
                return
            self._logged_in = True
            self._login_event.set()

        logger.info("mstock login confirmed")

        # Flush subscriptions now that the socket is logged in. The
        # adapter-supplied callback is authoritative when present (it replays
        # subscriptions requested before login); otherwise fall back to
        # replaying this client's own subscription dict.
        if self.on_login_callback:
            try:
                self.on_login_callback()
            except Exception as e:
                logger.error(f"Error in on_login callback: {e}")
        else:
            self._resubscribe_all()

    def _on_ws_message(self, ws, message):
        """Called for both binary and text messages"""
        if isinstance(message, bytes):
            # Parse binary packet
            if len(message) in [51, 123, 379] or len(message) >= 383:
                quote_data = self.parse_binary_packet(message)
                if quote_data and self.data_callback:
                    self.data_callback(quote_data)
        elif isinstance(message, str):
            logger.debug(f"Received string message: {message}")
            # A string frame (if mstock ever sends one) confirms login early;
            # otherwise the post-login settle timer handles it.
            self._confirm_login()

    def _on_ws_error(self, ws, error):
        """Called on WebSocket error"""
        logger.error(f"WebSocket error: {error}")
        self._connected = False

    def _on_ws_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket is closed"""
        logger.info(f"WebSocket closed (code={close_status_code}, msg={close_msg})")
        self._connected = False
        self._logged_in = False

    def _resubscribe_all(self):
        """Re-subscribe to all tracked subscriptions after reconnection"""
        for correlation_id, sub in list(self.subscriptions.items()):
            try:
                self.subscribe_stream(correlation_id, sub["token"], sub["exchange_type"], sub["mode"])
                logger.info(f"Re-subscribed to {sub['token']} mode {sub['mode']}")
            except Exception as e:
                logger.error(f"Error re-subscribing to {sub['token']}: {e}")

    def subscribe_stream(self, correlation_id: str, token: str, exchange_type: int, mode: int) -> bool:
        """
        Subscribe to a symbol on the persistent WebSocket connection.

        Args:
            correlation_id: Unique ID for this subscription
            token: Symbol token
            exchange_type: Exchange type code
            mode: Subscription mode
        """
        if not self._connected or not self.ws:
            logger.error("WebSocket not connected")
            return False

        try:
            subscribe_msg = {
                "action": 1,
                "params": {
                    "mode": mode,
                    "tokenList": [{"exchangeType": exchange_type, "tokens": [str(token)]}],
                },
            }

            self.ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to token {token} on exchange {exchange_type} with mode {mode}")

            self.subscriptions[correlation_id] = {
                "token": token,
                "exchange_type": exchange_type,
                "mode": mode,
            }
            return True

        except Exception as e:
            logger.error(f"Error subscribing: {str(e)}")
            return False

    def unsubscribe_stream(self, correlation_id: str) -> bool:
        """
        Unsubscribe from a symbol on the persistent WebSocket connection.

        Args:
            correlation_id: Unique ID of the subscription to remove
        """
        if not self._connected or not self.ws:
            return False

        try:
            if correlation_id not in self.subscriptions:
                return False

            sub = self.subscriptions[correlation_id]

            unsubscribe_msg = {
                "action": 0,
                "params": {
                    "mode": sub["mode"],
                    "tokenList": [{"exchangeType": sub["exchange_type"], "tokens": [str(sub["token"])]}],
                },
            }

            self.ws.send(json.dumps(unsubscribe_msg))
            logger.info(f"Unsubscribed from token {sub['token']}")

            del self.subscriptions[correlation_id]
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing: {str(e)}")
            return False

    def disconnect_stream(self):
        """Disconnect the persistent WebSocket connection"""
        self.running = False
        self._connected = False

        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")

        # Don't join threads — daemon threads stop on their own
        self._ws_thread = None
        logger.info("Streaming mode disconnected")

    def is_connected(self) -> bool:
        """Check if WebSocket is connected and logged in"""
        return self._connected and self._logged_in and self.running

    # ==================== One-off Fetch (sync) ====================

    def fetch_quote(self, token: str, exchange_type: int, mode: int = 3) -> dict | None:
        """
        Fetch a single quote synchronously using a temporary WebSocket connection.
        Uses websocket-client's create_connection for a simple request-response.
        """
        try:
            import websocket as ws_module
            ws = ws_module.create_connection(
                self.ws_url,
                sslopt={"cert_reqs": ssl.CERT_NONE},
                timeout=10,
            )

            # Send LOGIN
            ws.send(f"LOGIN:{self.auth_token}")

            # Wait for login response
            try:
                ws.recv()  # Login response
            except Exception:
                pass

            # Subscribe
            subscribe_msg = {
                "action": 1,
                "params": {
                    "mode": mode,
                    "tokenList": [{"exchangeType": exchange_type, "tokens": [str(token)]}],
                },
            }
            ws.send(json.dumps(subscribe_msg))

            # Wait for binary response
            for _ in range(3):
                try:
                    response = ws.recv()
                    if isinstance(response, bytes):
                        if len(response) in [51, 123, 379] or len(response) >= 383:
                            quote = self.parse_binary_packet(response)
                            if quote:
                                ws.close()
                                return quote
                except Exception:
                    break

            ws.close()
            return None

        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return None

    @classmethod
    def _split_packets(cls, data: bytes) -> list[dict]:
        """
        Split a raw WebSocket frame into one or more parsed quote dicts.

        A frame is either a single quote packet (51/123/379 bytes) or a batched
        frame (>=383 bytes) carrying a 4-byte header (num_packets, packet_size)
        followed by that many fixed-size packets.
        """
        quotes: list[dict] = []
        if len(data) in (51, 123, 379):
            quote = cls.parse_binary_packet(data)
            if quote:
                quotes.append(quote)
        elif len(data) >= 383:
            num_packets = struct.unpack("<H", data[0:2])[0]
            packet_size = struct.unpack("<H", data[2:4])[0] or 379
            for i in range(num_packets):
                chunk = data[4 + i * packet_size : 4 + (i + 1) * packet_size]
                if len(chunk) >= 51:
                    quote = cls.parse_binary_packet(chunk)
                    if quote:
                        quotes.append(quote)
        return quotes

    def fetch_quotes_bulk(
        self,
        token_requests: list[tuple[str, int]],
        mode: int = 3,
        timeout: float = 5.0,
    ) -> dict[str, dict]:
        """
        Fetch snap quotes for many tokens over a single WebSocket connection.

        mstock has no REST endpoint for open interest or market depth — the
        binary snap-quote feed (mode 3) is the only source. Opening one
        short-lived connection and subscribing to every token at once keeps a
        full option-chain fetch to well under a second.

        The login acknowledgement is NOT awaited: blocking on it stalls the
        socket ~10-15s, whereas the server accepts the subscribe and starts
        pushing snap quotes immediately after a brief settle.

        Args:
            token_requests: list of (token, exchange_type) tuples.
            mode: subscription mode (3 = snap quote with OI + depth).
            timeout: max seconds to wait for packets after subscribing.

        Returns:
            dict mapping token (str) -> parsed quote dict. Tokens for which no
            packet arrives within the timeout are simply absent.
        """
        import websocket as ws_module

        results: dict[str, dict] = {}
        if not token_requests:
            return results

        # Group tokens by exchange type for the subscribe payload
        tokens_by_type: dict[int, list[str]] = {}
        expected: set[str] = set()
        for token, exchange_type in token_requests:
            token = str(token)
            tokens_by_type.setdefault(exchange_type, []).append(token)
            expected.add(token)

        ws = None
        try:
            ws = ws_module.create_connection(
                self.ws_url,
                sslopt={"cert_reqs": ssl.CERT_NONE},
                timeout=10,
            )

            ws.send(f"LOGIN:{self.auth_token}")
            # Brief settle instead of a blocking login-response recv (see docstring)
            time.sleep(0.5)

            # Subscribe in chunks to stay within per-message token limits while
            # reusing the single connection.
            CHUNK = 100
            for exchange_type, tokens in tokens_by_type.items():
                for i in range(0, len(tokens), CHUNK):
                    subscribe_msg = {
                        "action": 1,
                        "params": {
                            "mode": mode,
                            "tokenList": [
                                {"exchangeType": exchange_type, "tokens": tokens[i : i + CHUNK]}
                            ],
                        },
                    }
                    ws.send(json.dumps(subscribe_msg))

            ws.settimeout(1.0)
            deadline = time.time() + timeout
            while time.time() < deadline and len(results) < len(expected):
                try:
                    message = ws.recv()
                except Exception:
                    continue
                if not isinstance(message, bytes):
                    continue
                for quote in self._split_packets(message):
                    token = quote.get("token")
                    if token in expected:
                        results[token] = quote

            logger.info(f"Bulk snap-quote: {len(results)}/{len(expected)} tokens received")
            return results

        except Exception as e:
            logger.error(f"Error in bulk quote fetch: {e}")
            return results
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass
