"""Integration tests for Pi42 Phase 4 features."""

import pytest
from unittest.mock import Mock, patch
from broker.pi42.api.funds_api import (
    get_account_balance,
    get_asset_balance,
    get_margin_info,
    get_available_balance,
    get_total_balance,
    get_income_history,
    transfer_funds,
    get_transfer_history
)
from broker.pi42.api.account_api import (
    get_account_info,
    get_trading_fees,
    get_api_key_permissions,
    get_account_trades,
    get_account_status,
    get_position_mode,
    change_position_mode
)


class TestFundsAPI:
    """Test funds and balance API."""

    @patch('broker.pi42.api.funds_api.requests.get')
    @patch('broker.pi42.api.funds_api.create_auth_instance')
    def test_get_account_balance_success(self, mock_auth, mock_get):
        """Test successful balance retrieval."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'asset': 'USDT',
                'walletBalance': '10000',
                'unrealizedProfit': '500',
                'marginBalance': '10500',
                'availableBalance': '8000',
                'crossWalletBalance': '10000',
                'crossUnPnl': '500',
                'maxWithdrawAmount': '8000'
            }
        ]
        mock_get.return_value = mock_response

        # Test
        result, status = get_account_balance('test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert len(result['data']) == 1
        assert result['data'][0]['asset'] == 'USDT'
        assert result['data'][0]['wallet_balance'] == 10000.0

    @patch('broker.pi42.api.funds_api.get_account_balance')
    def test_get_asset_balance_success(self, mock_get_balance):
        """Test get specific asset balance."""
        mock_get_balance.return_value = (
            {
                'status': 'success',
                'data': [
                    {'asset': 'USDT', 'available_balance': 8000.0},
                    {'asset': 'INR', 'available_balance': 50000.0}
                ]
            },
            200
        )

        result, status = get_asset_balance('USDT', 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['data']['asset'] == 'USDT'

    @patch('broker.pi42.api.funds_api.requests.get')
    @patch('broker.pi42.api.funds_api.create_auth_instance')
    def test_get_margin_info_success(self, mock_auth, mock_get):
        """Test margin info retrieval."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'totalWalletBalance': '10000',
            'totalUnrealizedProfit': '500',
            'totalMarginBalance': '10500',
            'availableBalance': '8000',
            'canTrade': True,
            'assets': [
                {
                    'asset': 'USDT',
                    'walletBalance': '10000',
                    'unrealizedProfit': '500',
                    'marginBalance': '10500',
                    'availableBalance': '8000'
                }
            ]
        }
        mock_get.return_value = mock_response

        # Test
        result, status = get_margin_info('test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['data']['can_trade'] is True
        assert len(result['data']['assets']) == 1

    @patch('broker.pi42.api.funds_api.requests.post')
    @patch('broker.pi42.api.funds_api.create_auth_instance')
    def test_transfer_funds_success(self, mock_auth, mock_post):
        """Test successful fund transfer."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'tranId': '12345'}
        mock_post.return_value = mock_response

        # Test
        result, status = transfer_funds('USDT', 1000.0, 'SPOT_TO_FUTURES', 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['tran_id'] == '12345'

    def test_transfer_funds_invalid_type(self):
        """Test transfer with invalid type."""
        result, status = transfer_funds('USDT', 1000.0, 'INVALID_TYPE', 'test_token')

        assert status == 400
        assert result['status'] == 'error'


class TestAccountAPI:
    """Test account management API."""

    @patch('broker.pi42.api.account_api.requests.get')
    @patch('broker.pi42.api.account_api.create_auth_instance')
    def test_get_account_info_success(self, mock_auth, mock_get):
        """Test account info retrieval."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'canTrade': True,
            'canDeposit': True,
            'canWithdraw': True,
            'feeTier': 0,
            'totalWalletBalance': '10000',
            'availableBalance': '8000'
        }
        mock_get.return_value = mock_response

        # Test
        result, status = get_account_info('test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['data']['can_trade'] is True

    @patch('broker.pi42.api.account_api.requests.get')
    @patch('broker.pi42.api.account_api.create_auth_instance')
    def test_get_trading_fees_success(self, mock_auth, mock_get):
        """Test trading fees retrieval."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': 'BTCUSDT',
            'makerCommissionRate': '0.0002',
            'takerCommissionRate': '0.0004'
        }
        mock_get.return_value = mock_response

        # Test
        result, status = get_trading_fees('BTCUSDT', 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['data']['maker_commission_rate'] == 0.0002
        assert result['data']['taker_commission_rate'] == 0.0004

    @patch('broker.pi42.api.account_api.requests.get')
    @patch('broker.pi42.api.account_api.create_auth_instance')
    def test_get_api_key_permissions_success(self, mock_auth, mock_get):
        """Test API key permissions retrieval."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'enableSpotAndMarginTrading': True,
            'enableWithdrawals': False,
            'enableReading': True,
            'enableFutures': True,
            'ipRestrict': False
        }
        mock_get.return_value = mock_response

        # Test
        result, status = get_api_key_permissions('test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['data']['can_trade'] is True
        assert result['data']['can_withdraw'] is False

    @patch('broker.pi42.api.account_api.requests.get')
    @patch('broker.pi42.api.account_api.create_auth_instance')
    def test_get_position_mode_success(self, mock_auth, mock_get):
        """Test position mode retrieval."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'dualSidePosition': True}
        mock_get.return_value = mock_response

        # Test
        result, status = get_position_mode('test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['data']['mode'] == 'HEDGE'

    @patch('broker.pi42.api.account_api.requests.post')
    @patch('broker.pi42.api.account_api.create_auth_instance')
    def test_change_position_mode_success(self, mock_auth, mock_post):
        """Test position mode change."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        # Test
        result, status = change_position_mode(True, 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['mode'] == 'HEDGE'

    @patch('broker.pi42.api.account_api.requests.get')
    @patch('broker.pi42.api.account_api.create_auth_instance')
    def test_get_account_trades_success(self, mock_auth, mock_get):
        """Test account trades retrieval."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'symbol': 'BTCUSDT',
                'id': '12345',
                'orderId': '67890',
                'side': 'BUY',
                'price': '50000',
                'qty': '0.1',
                'realizedPnl': '10',
                'commission': '0.5',
                'commissionAsset': 'USDT',
                'time': 1640000000000,
                'buyer': True,
                'maker': False
            }
        ]
        mock_get.return_value = mock_response

        # Test
        result, status = get_account_trades('BTCUSDT', 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert len(result['data']) == 1
        assert result['data'][0]['symbol'] == 'BTCUSDT'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
