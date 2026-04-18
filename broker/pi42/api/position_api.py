"""Pi42 position management API."""

import requests
from typing import Dict, Tuple, List
from broker.pi42.api.auth_api import create_auth_instance


def get_positions(auth_token: str) -> Tuple[Dict, int]:
    """
    Get all open positions from Pi42.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/position'
        headers, params = auth.sign_request('GET', endpoint, params={})

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            positions = response.json()

            # Transform to OpenAlgo format
            transformed = [_map_position_data(pos) for pos in positions]

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get positions: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def close_position(symbol: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Close position for symbol.

    Args:
        symbol: Trading symbol
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Get current position
        endpoint = '/v1/position'
        headers, params = auth.sign_request('GET', endpoint, params={'symbol': symbol})
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f"Failed to get position: {response.text}"
            }, response.status_code

        positions = response.json()
        if not positions:
            return {
                'status': 'error',
                'message': 'No position found for symbol'
            }, 404

        position = positions[0]
        position_amt = float(position.get('positionAmt', 0))

        if position_amt == 0:
            return {
                'status': 'success',
                'message': 'Position already closed'
            }, 200

        # Place closing order
        side = 'SELL' if position_amt > 0 else 'BUY'
        quantity = abs(position_amt)

        close_order = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
            'reduceOnly': True
        }

        endpoint = '/v1/order/place-order'
        headers, body = auth.sign_request('POST', endpoint, body=close_order)
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            result = response.json()
            return {
                'status': 'success',
                'orderid': result.get('orderId', ''),
                'message': 'Position closed successfully'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to close position: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def _map_position_data(position: Dict) -> Dict:
    """
    Map Pi42 position data to OpenAlgo format.

    Args:
        position: Pi42 position data

    Returns:
        OpenAlgo position data
    """
    position_amt = float(position.get('positionAmt', 0))
    entry_price = float(position.get('entryPrice', 0))
    mark_price = float(position.get('markPrice', 0))
    unrealized_pnl = float(position.get('unrealizedProfit', 0))

    return {
        'symbol': position.get('symbol', ''),
        'exchange': 'PI42',
        'product': 'FUTURES',
        'quantity': abs(position_amt),
        'side': 'LONG' if position_amt > 0 else 'SHORT' if position_amt < 0 else 'FLAT',
        'average_price': entry_price,
        'ltp': mark_price,
        'pnl': unrealized_pnl,
        'leverage': int(position.get('leverage', 1)),
        'margin_mode': position.get('marginType', 'CROSS'),
        'liquidation_price': float(position.get('liquidationPrice', 0)),
        'margin': float(position.get('isolatedMargin', 0))
    }
