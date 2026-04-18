"""Transform OpenAlgo data to Pi42 format."""

from typing import Dict


def transform_order_data(data: Dict) -> Dict:
    """
    Transform OpenAlgo order data to Pi42 format.

    Args:
        data: OpenAlgo order data

    Returns:
        Pi42 order data
    """
    # Map order type
    order_type_map = {
        'MARKET': 'MARKET',
        'LIMIT': 'LIMIT',
        'SL': 'STOP_LIMIT',
        'SL-M': 'STOP_MARKET'
    }

    pi42_data = {
        'symbol': data['symbol'],
        'side': data['action'],  # BUY or SELL
        'type': order_type_map.get(data['pricetype'], 'MARKET'),
        'quantity': float(data['quantity'])
    }

    # Add price for LIMIT orders
    if data['pricetype'] in ['LIMIT', 'SL']:
        pi42_data['price'] = float(data['price'])

    # Add stop price for STOP orders
    if data['pricetype'] in ['SL', 'SL-M']:
        pi42_data['stopPrice'] = float(data.get('trigger_price', data.get('price', 0)))

    # Add crypto-specific fields
    if 'leverage' in data:
        pi42_data['leverage'] = int(data['leverage'])

    if 'margin_mode' in data:
        pi42_data['marginMode'] = data['margin_mode']

    if 'margin_asset' in data:
        pi42_data['marginAsset'] = data['margin_asset']

    return pi42_data


def format_crypto_price(price: float, precision: int) -> float:
    """
    Format price to correct precision.

    Args:
        price: Price value
        precision: Decimal places

    Returns:
        Formatted price
    """
    return round(price, precision)


def format_crypto_quantity(quantity: float, precision: int) -> float:
    """
    Format quantity to correct precision.

    Args:
        quantity: Quantity value
        precision: Decimal places

    Returns:
        Formatted quantity
    """
    return round(quantity, precision)
