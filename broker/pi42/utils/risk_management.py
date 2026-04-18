"""Pi42 position risk management utilities."""

from typing import Dict, Optional
from database.symbol import db_session, SymToken


def calculate_position_risk(
    symbol: str,
    quantity: float,
    entry_price: float,
    leverage: int,
    margin_mode: str = 'CROSS'
) -> Dict:
    """
    Calculate position risk metrics.

    Args:
        symbol: Trading symbol
        quantity: Position quantity
        entry_price: Entry price
        leverage: Leverage multiplier
        margin_mode: ISOLATED or CROSS

    Returns:
        Risk metrics dictionary
    """
    # Get contract info
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        raise ValueError(f"Contract not found: {symbol}")

    # Calculate notional value
    notional_value = quantity * entry_price

    # Calculate required margin
    required_margin = notional_value / leverage

    # Calculate maintenance margin
    maintenance_margin_rate = contract.maintenance_margin_rate or 0.005
    maintenance_margin = notional_value * maintenance_margin_rate

    # Calculate liquidation price (simplified)
    if margin_mode == 'ISOLATED':
        # For long: liquidation = entry * (1 - 1/leverage + maintenance_margin_rate)
        # For short: liquidation = entry * (1 + 1/leverage - maintenance_margin_rate)
        liquidation_buffer = (1 / leverage) - maintenance_margin_rate
    else:
        # Cross margin liquidation depends on total account balance
        liquidation_buffer = 0.01  # Placeholder

    return {
        'symbol': symbol,
        'notional_value': notional_value,
        'required_margin': required_margin,
        'maintenance_margin': maintenance_margin,
        'maintenance_margin_rate': maintenance_margin_rate,
        'leverage': leverage,
        'margin_mode': margin_mode,
        'liquidation_buffer': liquidation_buffer,
        'max_leverage': contract.max_leverage
    }


def calculate_liquidation_price(
    entry_price: float,
    leverage: int,
    side: str,
    maintenance_margin_rate: float = 0.005
) -> float:
    """
    Calculate liquidation price for position.

    Args:
        entry_price: Entry price
        leverage: Leverage multiplier
        side: LONG or SHORT
        maintenance_margin_rate: Maintenance margin rate

    Returns:
        Liquidation price
    """
    if side == 'LONG':
        # Long liquidation: entry * (1 - 1/leverage + mmr)
        liquidation_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
    else:
        # Short liquidation: entry * (1 + 1/leverage - mmr)
        liquidation_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)

    return liquidation_price


def validate_order_risk(
    symbol: str,
    quantity: float,
    price: float,
    leverage: int,
    available_balance: float
) -> Dict:
    """
    Validate if order meets risk requirements.

    Args:
        symbol: Trading symbol
        quantity: Order quantity
        price: Order price
        leverage: Leverage multiplier
        available_balance: Available account balance

    Returns:
        Validation result dictionary
    """
    # Get contract info
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        return {
            'valid': False,
            'reason': f'Contract not found: {symbol}'
        }

    # Check quantity limits
    if quantity < contract.min_quantity:
        return {
            'valid': False,
            'reason': f'Quantity {quantity} below minimum {contract.min_quantity}'
        }

    if quantity > contract.max_quantity:
        return {
            'valid': False,
            'reason': f'Quantity {quantity} above maximum {contract.max_quantity}'
        }

    # Check leverage limits
    if leverage > contract.max_leverage:
        return {
            'valid': False,
            'reason': f'Leverage {leverage}x exceeds maximum {contract.max_leverage}x'
        }

    # Check notional value
    notional_value = quantity * price
    if notional_value < contract.min_notional:
        return {
            'valid': False,
            'reason': f'Notional value {notional_value} below minimum {contract.min_notional}'
        }

    # Check margin requirement
    required_margin = notional_value / leverage
    if required_margin > available_balance:
        return {
            'valid': False,
            'reason': f'Insufficient balance. Required: {required_margin}, Available: {available_balance}'
        }

    return {
        'valid': True,
        'required_margin': required_margin,
        'notional_value': notional_value
    }


def calculate_max_position_size(
    symbol: str,
    price: float,
    leverage: int,
    available_balance: float,
    risk_percentage: float = 1.0
) -> Dict:
    """
    Calculate maximum position size based on risk parameters.

    Args:
        symbol: Trading symbol
        price: Current price
        leverage: Leverage multiplier
        available_balance: Available account balance
        risk_percentage: Percentage of balance to risk (0-100)

    Returns:
        Position size calculation
    """
    # Get contract info
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        raise ValueError(f"Contract not found: {symbol}")

    # Calculate risk amount
    risk_amount = available_balance * (risk_percentage / 100)

    # Calculate max notional value
    max_notional = risk_amount * leverage

    # Calculate max quantity
    max_quantity = max_notional / price

    # Apply contract limits
    max_quantity = min(max_quantity, contract.max_quantity)
    max_quantity = max(max_quantity, contract.min_quantity)

    # Round to quantity precision
    quantity_precision = contract.quantity_precision or 3
    max_quantity = round(max_quantity, quantity_precision)

    # Calculate actual margin required
    actual_notional = max_quantity * price
    required_margin = actual_notional / leverage

    return {
        'symbol': symbol,
        'max_quantity': max_quantity,
        'price': price,
        'notional_value': actual_notional,
        'required_margin': required_margin,
        'leverage': leverage,
        'risk_percentage': risk_percentage,
        'available_balance': available_balance
    }


def check_position_health(
    entry_price: float,
    current_price: float,
    quantity: float,
    leverage: int,
    side: str,
    margin: float
) -> Dict:
    """
    Check position health and risk level.

    Args:
        entry_price: Entry price
        current_price: Current market price
        quantity: Position quantity
        leverage: Leverage multiplier
        side: LONG or SHORT
        margin: Position margin

    Returns:
        Position health metrics
    """
    # Calculate PnL
    if side == 'LONG':
        pnl = (current_price - entry_price) * quantity
    else:
        pnl = (entry_price - current_price) * quantity

    # Calculate margin ratio
    notional_value = quantity * current_price
    margin_ratio = (margin + pnl) / notional_value if notional_value > 0 else 0

    # Calculate liquidation distance
    liquidation_price = calculate_liquidation_price(entry_price, leverage, side)
    if side == 'LONG':
        liquidation_distance = ((current_price - liquidation_price) / current_price) * 100
    else:
        liquidation_distance = ((liquidation_price - current_price) / current_price) * 100

    # Determine risk level
    if liquidation_distance < 5:
        risk_level = 'CRITICAL'
    elif liquidation_distance < 15:
        risk_level = 'HIGH'
    elif liquidation_distance < 30:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    return {
        'pnl': pnl,
        'margin_ratio': margin_ratio,
        'liquidation_price': liquidation_price,
        'liquidation_distance_pct': liquidation_distance,
        'risk_level': risk_level,
        'current_price': current_price,
        'entry_price': entry_price
    }
