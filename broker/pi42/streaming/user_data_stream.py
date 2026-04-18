"""Pi42 user data streams."""

from typing import Dict, Callable
from broker.pi42.streaming.websocket_client import Pi42WebSocketClient


class Pi42UserDataStream:
    """Pi42 user data streaming."""

    def __init__(self, ws_client: Pi42WebSocketClient):
        """
        Initialize user data stream.

        Args:
            ws_client: WebSocket client instance
        """
        self.ws_client = ws_client
        self.listen_key = None

    def start_user_stream(self, callback: Callable):
        """
        Start user data stream.

        Args:
            callback: Callback function(data: Dict)
        """
        # In production, get listen key from REST API
        # For now, subscribe to user data channel
        channel = "userData"

        def user_data_callback(data: Dict):
            """Route user data to appropriate handler."""
            event_type = data.get('e')

            if event_type == 'ORDER_TRADE_UPDATE':
                self._handle_order_update(data, callback)
            elif event_type == 'ACCOUNT_UPDATE':
                self._handle_account_update(data, callback)
            elif event_type == 'MARGIN_CALL':
                self._handle_margin_call(data, callback)
            elif event_type == 'ACCOUNT_CONFIG_UPDATE':
                self._handle_config_update(data, callback)

        self.ws_client.subscribe(channel, user_data_callback)

    def _handle_order_update(self, data: Dict, callback: Callable):
        """Handle order update event."""
        o = data.get('o', {})
        processed = {
            'event_type': 'order',
            'event_time': data.get('E'),
            'symbol': o.get('s'),
            'client_order_id': o.get('c'),
            'side': o.get('S'),
            'order_type': o.get('o'),
            'time_in_force': o.get('f'),
            'quantity': float(o.get('q', 0)),
            'price': float(o.get('p', 0)),
            'stop_price': float(o.get('sp', 0)),
            'execution_type': o.get('x'),
            'order_status': o.get('X'),
            'order_id': o.get('i'),
            'last_filled_quantity': float(o.get('l', 0)),
            'cumulative_filled_quantity': float(o.get('z', 0)),
            'last_filled_price': float(o.get('L', 0)),
            'commission': float(o.get('n', 0)),
            'commission_asset': o.get('N'),
            'trade_time': o.get('T'),
            'trade_id': o.get('t'),
            'is_maker': o.get('m', False),
            'reduce_only': o.get('R', False),
            'working_type': o.get('wt'),
            'original_order_type': o.get('ot'),
            'position_side': o.get('ps'),
            'close_position': o.get('cp', False),
            'realized_profit': float(o.get('rp', 0))
        }
        callback(processed)

    def _handle_account_update(self, data: Dict, callback: Callable):
        """Handle account update event."""
        a = data.get('a', {})

        # Process balance updates
        balances = []
        for b in a.get('B', []):
            balances.append({
                'asset': b.get('a'),
                'wallet_balance': float(b.get('wb', 0)),
                'cross_wallet_balance': float(b.get('cw', 0)),
                'balance_change': float(b.get('bc', 0))
            })

        # Process position updates
        positions = []
        for p in a.get('P', []):
            positions.append({
                'symbol': p.get('s'),
                'position_amount': float(p.get('pa', 0)),
                'entry_price': float(p.get('ep', 0)),
                'accumulated_realized': float(p.get('cr', 0)),
                'unrealized_pnl': float(p.get('up', 0)),
                'margin_type': p.get('mt'),
                'isolated_wallet': float(p.get('iw', 0)),
                'position_side': p.get('ps')
            })

        processed = {
            'event_type': 'account',
            'event_time': data.get('E'),
            'transaction_time': data.get('T'),
            'balances': balances,
            'positions': positions
        }
        callback(processed)

    def _handle_margin_call(self, data: Dict, callback: Callable):
        """Handle margin call event."""
        positions = []
        for p in data.get('p', []):
            positions.append({
                'symbol': p.get('s'),
                'position_side': p.get('ps'),
                'position_amount': float(p.get('pa', 0)),
                'margin_type': p.get('mt'),
                'isolated_wallet': float(p.get('iw', 0)),
                'mark_price': float(p.get('mp', 0)),
                'unrealized_pnl': float(p.get('up', 0)),
                'maintenance_margin_required': float(p.get('mm', 0))
            })

        processed = {
            'event_type': 'margin_call',
            'event_time': data.get('E'),
            'cross_wallet_balance': float(data.get('cw', 0)),
            'positions': positions
        }
        callback(processed)

    def _handle_config_update(self, data: Dict, callback: Callable):
        """Handle account config update event."""
        ac = data.get('ac', {})
        ai = data.get('ai', {})

        processed = {
            'event_type': 'config',
            'event_time': data.get('E'),
            'transaction_time': data.get('T')
        }

        # Leverage update
        if ac:
            processed['leverage'] = {
                'symbol': ac.get('s'),
                'leverage': int(ac.get('l', 0))
            }

        # Multi-assets mode update
        if ai:
            processed['multi_assets_mode'] = ai.get('j', False)

        callback(processed)

    def stop_user_stream(self):
        """Stop user data stream."""
        self.ws_client.unsubscribe("userData")


class Pi42PositionStream:
    """Pi42 position-specific streaming."""

    def __init__(self, ws_client: Pi42WebSocketClient):
        """
        Initialize position stream.

        Args:
            ws_client: WebSocket client instance
        """
        self.ws_client = ws_client

    def subscribe_position_updates(self, callback: Callable):
        """
        Subscribe to position updates.

        Args:
            callback: Callback function(data: Dict)
        """
        channel = "position"

        def position_callback(data: Dict):
            """Process position update."""
            processed = {
                'event_type': 'position',
                'event_time': data.get('E'),
                'symbol': data.get('s'),
                'position_amount': float(data.get('pa', 0)),
                'entry_price': float(data.get('ep', 0)),
                'mark_price': float(data.get('mp', 0)),
                'unrealized_pnl': float(data.get('up', 0)),
                'accumulated_realized': float(data.get('cr', 0)),
                'margin_type': data.get('mt'),
                'isolated_wallet': float(data.get('iw', 0)),
                'leverage': int(data.get('l', 0)),
                'liquidation_price': float(data.get('lp', 0)),
                'position_side': data.get('ps')
            }
            callback(processed)

        self.ws_client.subscribe(channel, position_callback)

    def unsubscribe_position_updates(self):
        """Unsubscribe from position updates."""
        self.ws_client.unsubscribe("position")


class Pi42BalanceStream:
    """Pi42 balance-specific streaming."""

    def __init__(self, ws_client: Pi42WebSocketClient):
        """
        Initialize balance stream.

        Args:
            ws_client: WebSocket client instance
        """
        self.ws_client = ws_client

    def subscribe_balance_updates(self, callback: Callable):
        """
        Subscribe to balance updates.

        Args:
            callback: Callback function(data: Dict)
        """
        channel = "balance"

        def balance_callback(data: Dict):
            """Process balance update."""
            processed = {
                'event_type': 'balance',
                'event_time': data.get('E'),
                'asset': data.get('a'),
                'wallet_balance': float(data.get('wb', 0)),
                'cross_wallet_balance': float(data.get('cw', 0)),
                'balance_change': float(data.get('bc', 0)),
                'available_balance': float(data.get('ab', 0)),
                'margin_balance': float(data.get('mb', 0))
            }
            callback(processed)

        self.ws_client.subscribe(channel, balance_callback)

    def unsubscribe_balance_updates(self):
        """Unsubscribe from balance updates."""
        self.ws_client.unsubscribe("balance")
