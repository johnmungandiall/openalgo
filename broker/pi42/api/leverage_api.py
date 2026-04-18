"""Pi42 leverage and margin management API."""

import requests
from typing import Dict, Tuple
from broker.pi42.api.auth_api import create_auth_instance


def change_leverage(symbol: str, leverage: int, auth_token: str) -> Tuple[Dict, int]:
    """
    Change leverage for symbol.

    Args:
        symbol: Trading symbol
        leverage: Leverage value (1-150)
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Validate leverage
        if not 1 <= leverage <= 150:
            return {
                'status': 'error',
                'message': 'Leverage must be between 1 and 150'
            }, 400

        # Sign request
        endpoint = '/v1/leverage'
        body = {
            'symbol': symbol,
            'leverage': leverage
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            result = response.json()
            return {
                'status': 'success',
                'leverage': result.get('leverage', leverage),
                'symbol': symbol,
                'message': f'Leverage changed to {leverage}x'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to change leverage: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def change_margin_mode(symbol: str, margin_mode: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Change margin mode for symbol.

    Args:
        symbol: Trading symbol
        margin_mode: ISOLATED or CROSS
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Validate margin mode
        if margin_mode not in ['ISOLATED', 'CROSS']:
            return {
                'status': 'error',
                'message': 'Margin mode must be ISOLATED or CROSS'
            }, 400

        # Sign request
        endpoint = '/v1/marginType'
        body = {
            'symbol': symbol,
            'marginType': margin_mode
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            return {
                'status': 'success',
                'margin_mode': margin_mode,
                'symbol': symbol,
                'message': f'Margin mode changed to {margin_mode}'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to change margin mode: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def add_margin(symbol: str, amount: float, auth_token: str) -> Tuple[Dict, int]:
    """
    Add margin to isolated position.

    Args:
        symbol: Trading symbol
        amount: Margin amount to add
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/positionMargin'
        body = {
            'symbol': symbol,
            'amount': amount,
            'type': 1  # 1 = add, 2 = reduce
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            result = response.json()
            return {
                'status': 'success',
                'amount': amount,
                'symbol': symbol,
                'message': f'Added {amount} margin'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to add margin: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def reduce_margin(symbol: str, amount: float, auth_token: str) -> Tuple[Dict, int]:
    """
    Reduce margin from isolated position.

    Args:
        symbol: Trading symbol
        amount: Margin amount to reduce
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/positionMargin'
        body = {
            'symbol': symbol,
            'amount': amount,
            'type': 2  # 1 = add, 2 = reduce
        }
        headers, body = auth.sign_request('POST', endpoint, body=body)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            result = response.json()
            return {
                'status': 'success',
                'amount': amount,
                'symbol': symbol,
                'message': f'Reduced {amount} margin'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to reduce margin: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500


def get_leverage_brackets(symbol: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Get leverage brackets for symbol.

    Args:
        symbol: Trading symbol
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/leverageBracket'
        params = {'symbol': symbol}
        headers, params = auth.sign_request('GET', endpoint, params=params)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            brackets = response.json()
            return {
                'status': 'success',
                'data': brackets
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get leverage brackets: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500
