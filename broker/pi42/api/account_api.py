"""Pi42 account management API."""

import requests
from typing import Dict, Tuple, List, Optional
from broker.pi42.api.auth_api import create_auth_instance


def get_account_info(auth_token: str) -> Tuple[Dict, int]:
    """
    Get account information.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/account'
        headers, params = auth.sign_request('GET', endpoint, params={})

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            account = response.json()

            # Transform to OpenAlgo format
            transformed = {
                'account_type': 'FUTURES',
                'can_trade': account.get('canTrade', False),
                'can_deposit': account.get('canDeposit', False),
                'can_withdraw': account.get('canWithdraw', False),
                'fee_tier': account.get('feeTier', 0),
                'max_withdraw_amount': float(account.get('maxWithdrawAmount', 0)),
                'total_initial_margin': float(account.get('totalInitialMargin', 0)),
                'total_maintenance_margin': float(account.get('totalMaintenanceMargin', 0)),
                'total_wallet_balance': float(account.get('totalWalletBalance', 0)),
                'total_unrealized_profit': float(account.get('totalUnrealizedProfit', 0)),
                'total_margin_balance': float(account.get('totalMarginBalance', 0)),
                'total_position_initial_margin': float(account.get('totalPositionInitialMargin', 0)),
                'total_open_order_initial_margin': float(account.get('totalOpenOrderInitialMargin', 0)),
                'total_cross_wallet_balance': float(account.get('totalCrossWalletBalance', 0)),
                'total_cross_unrealized_pnl': float(account.get('totalCrossUnPnl', 0)),
                'available_balance': float(account.get('availableBalance', 0)),
                'update_time': account.get('updateTime')
            }

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get account info: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_trading_fees(symbol: Optional[str] = None, auth_token: str = None) -> Tuple[Dict, int]:
    """
    Get trading fee rates.

    Args:
        symbol: Trading symbol (optional)
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Build params
        params = {}
        if symbol:
            params['symbol'] = symbol

        # Sign request
        endpoint = '/v1/commissionRate'
        headers, params = auth.sign_request('GET', endpoint, params=params)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            fee_data = response.json()

            # Transform to OpenAlgo format
            transformed = {
                'symbol': fee_data.get('symbol'),
                'maker_commission_rate': float(fee_data.get('makerCommissionRate', 0)),
                'taker_commission_rate': float(fee_data.get('takerCommissionRate', 0)),
                'maker_commission_rate_pct': float(fee_data.get('makerCommissionRate', 0)) * 100,
                'taker_commission_rate_pct': float(fee_data.get('takerCommissionRate', 0)) * 100
            }

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get trading fees: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_api_key_permissions(auth_token: str) -> Tuple[Dict, int]:
    """
    Get API key permissions.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/apiKey/permissions'
        headers, params = auth.sign_request('GET', endpoint, params={})

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            permissions = response.json()

            # Transform to OpenAlgo format
            transformed = {
                'can_trade': permissions.get('enableSpotAndMarginTrading', False),
                'can_withdraw': permissions.get('enableWithdrawals', False),
                'can_read': permissions.get('enableReading', True),
                'can_futures': permissions.get('enableFutures', False),
                'ip_restrict': permissions.get('ipRestrict', False),
                'create_time': permissions.get('createTime'),
                'trading_authority_expiration_time': permissions.get('tradingAuthorityExpirationTime')
            }

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get API permissions: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_account_trades(
    symbol: str,
    auth_token: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    from_id: Optional[int] = None,
    limit: int = 100
) -> Tuple[Dict, int]:
    """
    Get account trade history.

    Args:
        symbol: Trading symbol
        auth_token: Encrypted auth token
        start_time: Start timestamp (ms)
        end_time: End timestamp (ms)
        from_id: Trade ID to fetch from
        limit: Number of records

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Build params
        params = {
            'symbol': symbol,
            'limit': limit
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        if from_id:
            params['fromId'] = from_id

        # Sign request
        endpoint = '/v1/userTrades'
        headers, params = auth.sign_request('GET', endpoint, params=params)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            trades = response.json()

            # Transform to OpenAlgo format
            transformed = []
            for trade in trades:
                transformed.append({
                    'symbol': trade.get('symbol'),
                    'trade_id': trade.get('id'),
                    'order_id': trade.get('orderId'),
                    'side': trade.get('side'),
                    'price': float(trade.get('price', 0)),
                    'quantity': float(trade.get('qty', 0)),
                    'realized_pnl': float(trade.get('realizedPnl', 0)),
                    'margin_asset': trade.get('marginAsset'),
                    'quote_qty': float(trade.get('quoteQty', 0)),
                    'commission': float(trade.get('commission', 0)),
                    'commission_asset': trade.get('commissionAsset'),
                    'time': trade.get('time'),
                    'position_side': trade.get('positionSide'),
                    'buyer': trade.get('buyer', False),
                    'maker': trade.get('maker', False)
                })

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get trades: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_account_status(auth_token: str) -> Tuple[Dict, int]:
    """
    Get account status and restrictions.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/account/status'
        headers, params = auth.sign_request('GET', endpoint, params={})

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            status = response.json()

            # Transform to OpenAlgo format
            transformed = {
                'data': status.get('data', 'Normal'),
                'msg': status.get('msg', ''),
                'is_locked': status.get('data') == 'Locked',
                'is_normal': status.get('data') == 'Normal'
            }

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get account status: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_position_mode(auth_token: str) -> Tuple[Dict, int]:
    """
    Get position mode (Hedge Mode or One-way Mode).

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/positionSide/dual'
        headers, params = auth.sign_request('GET', endpoint, params={})

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            mode = response.json()

            # Transform to OpenAlgo format
            dual_side = mode.get('dualSidePosition', False)
            transformed = {
                'dual_side_position': dual_side,
                'mode': 'HEDGE' if dual_side else 'ONE_WAY',
                'description': 'Hedge Mode (Long and Short positions)' if dual_side else 'One-way Mode (Net position)'
            }

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get position mode: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def change_position_mode(dual_side: bool, auth_token: str) -> Tuple[Dict, int]:
    """
    Change position mode.

    Args:
        dual_side: True for Hedge Mode, False for One-way Mode
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/positionSide/dual'
        body = {'dualSidePosition': dual_side}
        headers, body = auth.sign_request('POST', endpoint, body=body)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            mode = 'HEDGE' if dual_side else 'ONE_WAY'
            return {
                'status': 'success',
                'mode': mode,
                'message': f'Position mode changed to {mode}'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to change position mode: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500
