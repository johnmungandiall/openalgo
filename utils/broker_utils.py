"""Broker type detection utilities."""

STOCK_BROKERS = ['zerodha', 'dhan', 'fyers', 'kotak', 'angel', 'aliceblue', 'fivepaisa',
                 'fivepaisaxts', 'compositedge', 'dhan_sandbox', 'definedge', 'firstock',
                 'flattrade', 'groww', 'ibulls', 'iifl', 'iiflcapital', 'indmoney',
                 'jainamxts', 'motilal', 'mstock', 'nubra', 'paytm', 'pocketful',
                 'rmoney', 'samco', 'shoonya', 'tradejini', 'upstox', 'wisdom', 'zebu']

CRYPTO_BROKERS = ['pi42', 'deltaexchange']


def get_broker_type(broker_name: str) -> str:
    """
    Get broker type from broker name.

    Args:
        broker_name: Broker identifier

    Returns:
        'IN_stock' or 'CRYPTO_futures'
    """
    broker_lower = broker_name.lower()

    if broker_lower in CRYPTO_BROKERS:
        return 'CRYPTO_futures'
    elif broker_lower in STOCK_BROKERS:
        return 'IN_stock'
    else:
        # Default to stock for unknown brokers
        return 'IN_stock'


def is_crypto_broker(broker_name: str) -> bool:
    """Check if broker is crypto exchange."""
    return get_broker_type(broker_name) == 'CRYPTO_futures'


def is_stock_broker(broker_name: str) -> bool:
    """Check if broker is stock exchange."""
    return get_broker_type(broker_name) == 'IN_stock'
