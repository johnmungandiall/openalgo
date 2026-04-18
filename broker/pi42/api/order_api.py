"""Pi42 order management API."""

import requests
from typing import Dict, Tuple, Optional
from broker.pi42.api.auth_api import create_auth_instance
from broker.pi42.api.rate_limiter import rate_limiter


def place_order_api(data: Dict, auth_token: str) -> Tuple[Dict, int]:
    """
    Place order on Pi42.

    Args:
        data: Order data in OpenAlgo format
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        # Create auth instance
        auth = create_auth_instance(auth_token)

        # Transform to Pi42 format
        from broker.pi42.mapping.transform_data import transform_order_data
        pi42_data = transform_order_data(data)

        # Rate limit check
        rate_limiter.wait_if_needed('place_order')

        # Sign request
        endpoint = '/v1/order/place-order'
        headers, body = auth.sign_request('POST', endpoint, body=pi42_data)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            result = response.json()
            order_id = result.get('orderId', '')

            return {
                'status': 'success',
                'orderid': order_id,
                'message': 'Order placed successfully'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Order failed: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Order error: {str(e)}"
        }, 500


def cancel_order_api(order_id: str, auth_token: str) -> Tuple[Dict, int]:
    """
    Cancel order on Pi42.

    Args:
        order_id: Order ID to cancel
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Rate limit check
        rate_limiter.wait_if_needed('cancel_order')

        # Sign request
        endpoint = '/v1/order/cancel-order'
        body = {'orderId': order_id}
        headers, body = auth.sign_request('POST', endpoint, body=body)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            return {
                'status': 'success',
                'orderid': order_id,
                'message': 'Order cancelled successfully'
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Cancel failed: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Cancel error: {str(e)}"
        }, 500


def get_order_book(auth_token: str) -> Tuple[Dict, int]:
    """
    Get all orders from Pi42.

    Args:
        auth_token: Encrypted auth token

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        auth = create_auth_instance(auth_token)

        # Sign request
        endpoint = '/v1/order/open-orders'
        headers, _ = auth.sign_request('GET', endpoint)

        # Make request
        url = f"{auth.base_url}{endpoint}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            orders = response.json()

            # Transform to OpenAlgo format
            from broker.pi42.mapping.order_data import map_order_data
            transformed = [map_order_data(order) for order in orders]

            return {
                'status': 'success',
                'data': transformed
            }, 200
        else:
            return {
                'status': 'error',
                'message': f"Failed to get orders: {response.text}"
            }, response.status_code

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }, 500
