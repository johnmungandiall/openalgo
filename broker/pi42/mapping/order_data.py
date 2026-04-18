"""Map Pi42 order data to OpenAlgo format."""

from typing import Dict


def map_order_data(order: Dict) -> Dict:
    """
    Map Pi42 order to OpenAlgo format.

    Args:
        order: Pi42 order data

    Returns:
        OpenAlgo order data
    """
    # Map order status
    status_map = {
        'NEW': 'open',
        'PARTIALLY_FILLED': 'open',
        'FILLED': 'complete',
        'CANCELED': 'cancelled',
        'REJECTED': 'rejected',
        'EXPIRED': 'cancelled'
    }

    # Map order type
    type_map = {
        'MARKET': 'MARKET',
        'LIMIT': 'LIMIT',
        'STOP_MARKET': 'SL-M',
        'STOP_LIMIT': 'SL'
    }

    return {
        'symbol': order['symbol'],
        'exchange': 'PI42',
        'action': order['side'],
        'quantity': float(order['origQty']),
        'price': float(order.get('price', 0)),
        'trigger_price': float(order.get('stopPrice', 0)),
        'pricetype': type_map.get(order['type'], 'MARKET'),
        'product': order.get('marginMode', 'ISOLATED'),
        'orderid': order['orderId'],
        'order_status': status_map.get(order['status'], 'pending'),
        'timestamp': order.get('time', ''),
        'filled_quantity': float(order.get('executedQty', 0)),
        'pending_quantity': float(order['origQty']) - float(order.get('executedQty', 0)),
        'average_price': float(order.get('avgPrice', 0))
    }
