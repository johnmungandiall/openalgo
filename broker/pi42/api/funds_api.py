"""Pi42 funds and account balance API."""

import requests
from typing import Dict, Tuple, List, Optional
from broker.pi42.api.auth_api import create_auth_instance


def get_account_balance(auth_token: str) -> Tuple[Dict, int]:
    """
    Get account balance for all assets.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/account/balance'
        headers, params = auth.sign_request('GET', endpoint, params={})

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            balances = response.json()

            # Transform to OpenAlgo format
            transformed = []
            for balance in balances:
                transformed.append({
                    'asset': balance.get('asset'),
                    'wallet_balance': float(balance.get('walletBalance', 0)),
                    'unrealized_profit': float(balance.get('unrealizedProfit', 0)),
                    'margin_balance': float(balance.get('marginBalance', 0)),
                    'available_balance': float(balance.get('availableBalance', 0)),
                    'cross_wallet_balance': float(balance.get('crossWalletBalance', 0)),
                    'cross_unrealized_pnl': float(balance.get('crossUnPnl', 0)),
                    'max_withdraw_amount': float(balance.get('maxWithdrawAmount', 0))
                })

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get balance: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_asset_balance(asset: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Get balance for specific asset.

    Args:
        asset: Asset symbol (e.g., 'USDT', 'INR')
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        result, status = get_account_balance(auth_token)

        if status != 200:
            return result, status

        # Find specific asset
        for balance in result['data']:
            if balance['asset'] == asset:
                return {
                    'status': 'success',
                    'data': balance
                }, 200

        return {
            'status': 'error',
            'message': f'Asset {asset} not found'
        }, 404

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_margin_info(auth_token: str) -> Tuple[Dict, int]:
    """
    Get margin account information.

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
                'total_wallet_balance': float(account.get('totalWalletBalance', 0)),
                'total_unrealized_profit': float(account.get('totalUnrealizedProfit', 0)),
                'total_margin_balance': float(account.get('totalMarginBalance', 0)),
                'total_position_initial_margin': float(account.get('totalPositionInitialMargin', 0)),
                'total_open_order_initial_margin': float(account.get('totalOpenOrderInitialMargin', 0)),
                'total_cross_wallet_balance': float(account.get('totalCrossWalletBalance', 0)),
                'total_cross_unrealized_pnl': float(account.get('totalCrossUnPnl', 0)),
                'available_balance': float(account.get('availableBalance', 0)),
                'max_withdraw_amount': float(account.get('maxWithdrawAmount', 0)),
                'can_trade': account.get('canTrade', False),
                'can_deposit': account.get('canDeposit', False),
                'can_withdraw': account.get('canWithdraw', False),
                'update_time': account.get('updateTime')
            }

            # Add asset-specific balances
            assets = []
            for asset in account.get('assets', []):
                assets.append({
                    'asset': asset.get('asset'),
                    'wallet_balance': float(asset.get('walletBalance', 0)),
                    'unrealized_profit': float(asset.get('unrealizedProfit', 0)),
                    'margin_balance': float(asset.get('marginBalance', 0)),
                    'available_balance': float(asset.get('availableBalance', 0))
                })

            transformed['assets'] = assets

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get margin info: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_available_balance(asset: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Get available balance for trading.

    Args:
        asset: Asset symbol
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        result, status = get_asset_balance(asset, auth_token)

        if status != 200:
            return result, status

        available = result['data']['available_balance']

        return {
            'status': 'success',
            'asset': asset,
            'available_balance': available
        }, 200

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_total_balance(auth_token: str) -> Tuple[Dict, int]:
    """
    Get total account balance across all assets.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        result, status = get_margin_info(auth_token)

        if status != 200:
            return result, status

        data = result['data']

        return {
            'status': 'success',
            'total_wallet_balance': data['total_wallet_balance'],
            'total_margin_balance': data['total_margin_balance'],
            'available_balance': data['available_balance'],
            'total_unrealized_profit': data['total_unrealized_profit']
        }, 200

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_income_history(
    auth_token: str,
    symbol: Optional[str] = None,
    income_type: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100
) -> Tuple[Dict, int]:
    """
    Get income history (funding fees, realized PnL, etc.).

    Args:
        auth_token: Encrypted auth token
        symbol: Trading symbol (optional)
        income_type: Income type (TRANSFER, REALIZED_PNL, FUNDING_FEE, etc.)
        start_time: Start timestamp (ms)
        end_time: End timestamp (ms)
        limit: Number of records

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Build params
        params = {'limit': limit}
        if symbol:
            params['symbol'] = symbol
        if income_type:
            params['incomeType'] = income_type
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        # Sign request
        endpoint = '/v1/income'
        headers, params = auth.sign_request('GET', endpoint, params=params)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            income_records = response.json()

            # Transform to OpenAlgo format
            transformed = []
            for record in income_records:
                transformed.append({
                    'symbol': record.get('symbol'),
                    'income_type': record.get('incomeType'),
                    'income': float(record.get('income', 0)),
                    'asset': record.get('asset'),
                    'info': record.get('info'),
                    'time': record.get('time'),
                    'tran_id': record.get('tranId'),
                    'trade_id': record.get('tradeId')
                })

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get income history: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def transfer_funds(
    asset: str,
    amount: float,
    transfer_type: str,
    auth_token: str
) -> Tuple[Dict, int]:
    """
    Transfer funds between wallets.

    Args:
        asset: Asset to transfer (e.g., 'USDT', 'INR')
        amount: Transfer amount
        transfer_type: Transfer type (SPOT_TO_FUTURES, FUTURES_TO_SPOT)
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Map transfer type
        type_map = {
            'SPOT_TO_FUTURES': 1,
            'FUTURES_TO_SPOT': 2
        }

        if transfer_type not in type_map:
            return {
                'status': 'error',
                'message': f'Invalid transfer type: {transfer_type}'
            }, 400

        # Sign request
        endpoint = '/v1/futures/transfer'
        body = {
            'asset': asset,
            'amount': amount,
            'type': type_map[transfer_type]
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            result = response.json()

            return {
                'status': 'success',
                'tran_id': result.get('tranId'),
                'asset': asset,
                'amount': amount,
                'transfer_type': transfer_type,
                'message': f'Transferred {amount} {asset}'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Transfer failed: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_transfer_history(
    auth_token: str,
    asset: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100
) -> Tuple[Dict, int]:
    """
    Get transfer history.

    Args:
        auth_token: Encrypted auth token
        asset: Asset symbol (optional)
        start_time: Start timestamp (ms)
        end_time: End timestamp (ms)
        limit: Number of records

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Build params
        params = {'limit': limit}
        if asset:
            params['asset'] = asset
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        # Sign request
        endpoint = '/v1/futures/transfer'
        headers, params = auth.sign_request('GET', endpoint, params=params)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            transfers = response.json()

            # Transform to OpenAlgo format
            type_map = {1: 'SPOT_TO_FUTURES', 2: 'FUTURES_TO_SPOT'}
            transformed = []
            for transfer in transfers:
                transformed.append({
                    'asset': transfer.get('asset'),
                    'amount': float(transfer.get('amount', 0)),
                    'transfer_type': type_map.get(transfer.get('type'), 'UNKNOWN'),
                    'status': transfer.get('status'),
                    'tran_id': transfer.get('tranId'),
                    'time': transfer.get('timestamp')
                })

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get transfer history: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500
