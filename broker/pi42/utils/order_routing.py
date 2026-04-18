"""Pi42 smart order routing utilities."""

from typing import Dict, List, Optional, Tuple
from database.symbol import db_session, SymToken
from broker.pi42.utils.risk_management import validate_order_risk


def route_order(
    symbol: str,
    quantity: float,
    price: Optional[float],
    order_type: str,
    side: str,
    available_balance: float,
    leverage: int = 1
) -> Dict:
    """
    Smart order routing with validation and optimization.

    Args:
        symbol: Trading symbol
        quantity: Order quantity
        price: Order price (None for MARKET)
        order_type: MARKET, LIMIT, STOP_MARKET, STOP_LIMIT
        side: BUY or SELL
        available_balance: Available account balance
        leverage: Leverage multiplier

    Returns:
        Routing decision dictionary
    """
    # Get contract info
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        return {
            'status': 'error',
            'reason': f'Contract not found: {symbol}'
        }

    # Use current price for MARKET orders
    if price is None:
        # In production, fetch current market price
        price = 0  # Placeholder

    # Validate order risk
    validation = validate_order_risk(
        symbol=symbol,
        quantity=quantity,
        price=price,
        leverage=leverage,
        available_balance=available_balance
    )

    if not validation['valid']:
        return {
            'status': 'error',
            'reason': validation['reason']
        }

    # Apply quantity precision
    quantity_precision = contract.quantity_precision or 3
    adjusted_quantity = round(quantity, quantity_precision)

    # Apply price precision for LIMIT orders
    if order_type in ['LIMIT', 'STOP_LIMIT']:
        price_precision = contract.price_precision or 2
        adjusted_price = round(price, price_precision)
    else:
        adjusted_price = price

    # Determine optimal order parameters
    routing_params = {
        'symbol': symbol,
        'quantity': adjusted_quantity,
        'price': adjusted_price,
        'type': order_type,
        'side': side,
        'leverage': leverage
    }

    # Add time in force for LIMIT orders
    if order_type in ['LIMIT', 'STOP_LIMIT']:
        routing_params['timeInForce'] = 'GTC'  # Good Till Cancel

    # Add post-only for maker orders (optional optimization)
    if order_type == 'LIMIT':
        routing_params['postOnly'] = False  # Can be enabled for maker rebates

    return {
        'status': 'success',
        'routing_params': routing_params,
        'required_margin': validation['required_margin'],
        'notional_value': validation['notional_value']
    }


def split_large_order(
    symbol: str,
    total_quantity: float,
    max_chunk_size: Optional[float] = None
) -> List[float]:
    """
    Split large order into smaller chunks.

    Args:
        symbol: Trading symbol
        total_quantity: Total order quantity
        max_chunk_size: Maximum chunk size (None = use contract max)

    Returns:
        List of chunk quantities
    """
    # Get contract info
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        raise ValueError(f"Contract not found: {symbol}")

    # Determine chunk size
    if max_chunk_size is None:
        max_chunk_size = contract.max_quantity

    # Calculate number of chunks
    num_chunks = int(total_quantity / max_chunk_size) + 1
    chunk_size = total_quantity / num_chunks

    # Apply quantity precision
    quantity_precision = contract.quantity_precision or 3
    chunks = [round(chunk_size, quantity_precision) for _ in range(num_chunks)]

    # Adjust last chunk for rounding errors
    total_chunks = sum(chunks)
    if total_chunks != total_quantity:
        chunks[-1] = round(total_quantity - sum(chunks[:-1]), quantity_precision)

    return chunks


def optimize_order_execution(
    symbol: str,
    quantity: float,
    side: str,
    urgency: str = 'NORMAL'
) -> Dict:
    """
    Optimize order execution strategy.

    Args:
        symbol: Trading symbol
        quantity: Order quantity
        side: BUY or SELL
        urgency: LOW, NORMAL, HIGH

    Returns:
        Execution strategy
    """
    # Get contract info
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        raise ValueError(f"Contract not found: {symbol}")

    # Determine strategy based on urgency
    if urgency == 'HIGH':
        # Immediate execution with MARKET order
        strategy = {
            'order_type': 'MARKET',
            'split_order': False,
            'post_only': False,
            'time_in_force': 'IOC'  # Immediate or Cancel
        }
    elif urgency == 'LOW':
        # Patient execution with LIMIT order
        strategy = {
            'order_type': 'LIMIT',
            'split_order': quantity > contract.max_quantity * 0.5,
            'post_only': True,  # Maker only for rebates
            'time_in_force': 'GTC'
        }
    else:  # NORMAL
        # Balanced execution
        strategy = {
            'order_type': 'LIMIT',
            'split_order': quantity > contract.max_quantity * 0.8,
            'post_only': False,
            'time_in_force': 'GTC'
        }

    # Calculate chunks if splitting
    if strategy['split_order']:
        chunks = split_large_order(symbol, quantity)
        strategy['chunks'] = chunks
        strategy['num_chunks'] = len(chunks)

    return strategy


def calculate_slippage_estimate(
    symbol: str,
    quantity: float,
    side: str,
    current_price: float,
    order_book_depth: Optional[List[Tuple[float, float]]] = None
) -> Dict:
    """
    Estimate slippage for order.

    Args:
        symbol: Trading symbol
        quantity: Order quantity
        side: BUY or SELL
        current_price: Current market price
        order_book_depth: Order book data [(price, quantity), ...]

    Returns:
        Slippage estimate
    """
    if order_book_depth is None:
        # Simple estimate without order book
        # Assume 0.1% slippage for every 10% of max quantity
        contract = db_session.query(SymToken).filter_by(
            symbol=symbol,
            exchange='PI42'
        ).first()

        if not contract:
            raise ValueError(f"Contract not found: {symbol}")

        quantity_ratio = quantity / contract.max_quantity
        estimated_slippage_pct = quantity_ratio * 0.1

        estimated_price = current_price * (1 + estimated_slippage_pct if side == 'BUY' else 1 - estimated_slippage_pct)

        return {
            'estimated_slippage_pct': estimated_slippage_pct * 100,
            'estimated_price': estimated_price,
            'current_price': current_price,
            'method': 'simple'
        }

    # Calculate slippage from order book
    remaining_quantity = quantity
    total_cost = 0
    levels_consumed = 0

    for price, available_qty in order_book_depth:
        if remaining_quantity <= 0:
            break

        fill_qty = min(remaining_quantity, available_qty)
        total_cost += fill_qty * price
        remaining_quantity -= fill_qty
        levels_consumed += 1

    if remaining_quantity > 0:
        # Not enough liquidity
        return {
            'status': 'error',
            'reason': 'Insufficient liquidity',
            'remaining_quantity': remaining_quantity
        }

    average_price = total_cost / quantity
    slippage_pct = abs((average_price - current_price) / current_price) * 100

    return {
        'estimated_slippage_pct': slippage_pct,
        'estimated_price': average_price,
        'current_price': current_price,
        'levels_consumed': levels_consumed,
        'method': 'order_book'
    }


def suggest_order_improvements(
    symbol: str,
    quantity: float,
    price: Optional[float],
    order_type: str,
    side: str
) -> List[str]:
    """
    Suggest improvements for order parameters.

    Args:
        symbol: Trading symbol
        quantity: Order quantity
        price: Order price
        order_type: Order type
        side: BUY or SELL

    Returns:
        List of suggestions
    """
    suggestions = []

    # Get contract info
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        return ['Contract not found']

    # Check quantity optimization
    if quantity < contract.min_quantity * 2:
        suggestions.append(f'Consider increasing quantity above {contract.min_quantity * 2} for better execution')

    if quantity > contract.max_quantity * 0.9:
        suggestions.append('Consider splitting large order into multiple chunks')

    # Check order type optimization
    if order_type == 'MARKET':
        suggestions.append('Consider using LIMIT order to avoid slippage')

    if order_type == 'LIMIT' and price:
        # Check if price is too far from market
        # In production, compare with current market price
        suggestions.append('Verify limit price is close to market for faster execution')

    # Check leverage optimization
    if contract.max_leverage > 10:
        suggestions.append(f'High leverage available (up to {contract.max_leverage}x) - use with caution')

    return suggestions
