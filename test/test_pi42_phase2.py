"""Integration tests for Pi42 Phase 2 features."""

import pytest
from unittest.mock import Mock, patch
from broker.pi42.api.position_api import get_positions, close_position
from broker.pi42.api.leverage_api import change_leverage, change_margin_mode, add_margin, reduce_margin
from broker.pi42.utils.risk_management import (
    calculate_position_risk,
    calculate_liquidation_price,
    validate_order_risk,
    calculate_max_position_size,
    check_position_health
)
from broker.pi42.utils.order_routing import (
    route_order,
    split_large_order,
    optimize_order_execution,
    calculate_slippage_estimate
)


class TestPositionAPI:
    """Test position management API."""

    @patch('broker.pi42.api.position_api.requests.get')
    @patch('broker.pi42.api.position_api.create_auth_instance')
    def test_get_positions_success(self, mock_auth, mock_get):
        """Test successful position retrieval."""
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
                'positionAmt': '0.5',
                'entryPrice': '50000',
                'markPrice': '51000',
                'unrealizedProfit': '500',
                'leverage': '10',
                'marginType': 'CROSS',
                'liquidationPrice': '45000',
                'isolatedMargin': '0'
            }
        ]
        mock_get.return_value = mock_response

        # Test
        result, status = get_positions('test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert len(result['data']) == 1
        assert result['data'][0]['symbol'] == 'BTCUSDT'
        assert result['data'][0]['side'] == 'LONG'

    @patch('broker.pi42.api.position_api.requests.get')
    @patch('broker.pi42.api.position_api.requests.post')
    @patch('broker.pi42.api.position_api.create_auth_instance')
    def test_close_position_success(self, mock_auth, mock_post, mock_get):
        """Test successful position closure."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock get position response
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [
            {'symbol': 'BTCUSDT', 'positionAmt': '0.5'}
        ]
        mock_get.return_value = mock_get_response

        # Mock close order response
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {'orderId': '12345'}
        mock_post.return_value = mock_post_response

        # Test
        result, status = close_position('BTCUSDT', 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert 'orderid' in result


class TestLeverageAPI:
    """Test leverage and margin API."""

    @patch('broker.pi42.api.leverage_api.requests.post')
    @patch('broker.pi42.api.leverage_api.create_auth_instance')
    def test_change_leverage_success(self, mock_auth, mock_post):
        """Test successful leverage change."""
        # Mock auth
        mock_auth_instance = Mock()
        mock_auth_instance.base_url = 'https://fapi.pi42.com'
        mock_auth_instance.sign_request.return_value = ({'api-key': 'test'}, {})
        mock_auth.return_value = mock_auth_instance

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'leverage': 20}
        mock_post.return_value = mock_response

        # Test
        result, status = change_leverage('BTCUSDT', 20, 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['leverage'] == 20

    def test_change_leverage_invalid(self):
        """Test leverage validation."""
        result, status = change_leverage('BTCUSDT', 200, 'test_token')

        assert status == 400
        assert result['status'] == 'error'
        assert 'between 1 and 150' in result['message']

    @patch('broker.pi42.api.leverage_api.requests.post')
    @patch('broker.pi42.api.leverage_api.create_auth_instance')
    def test_add_margin_success(self, mock_auth, mock_post):
        """Test successful margin addition."""
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
        result, status = add_margin('BTCUSDT', 100.0, 'test_token')

        assert status == 200
        assert result['status'] == 'success'
        assert result['amount'] == 100.0


class TestRiskManagement:
    """Test risk management utilities."""

    def test_calculate_liquidation_price_long(self):
        """Test liquidation price calculation for long position."""
        liq_price = calculate_liquidation_price(
            entry_price=50000,
            leverage=10,
            side='LONG',
            maintenance_margin_rate=0.005
        )

        # Long liquidation: 50000 * (1 - 1/10 + 0.005) = 45250
        assert abs(liq_price - 45250) < 1

    def test_calculate_liquidation_price_short(self):
        """Test liquidation price calculation for short position."""
        liq_price = calculate_liquidation_price(
            entry_price=50000,
            leverage=10,
            side='SHORT',
            maintenance_margin_rate=0.005
        )

        # Short liquidation: 50000 * (1 + 1/10 - 0.005) = 54750
        assert abs(liq_price - 54750) < 1

    @patch('broker.pi42.utils.risk_management.db_session')
    def test_validate_order_risk_quantity_too_low(self, mock_db):
        """Test order validation with quantity below minimum."""
        # Mock contract
        mock_contract = Mock()
        mock_contract.min_quantity = 0.01
        mock_contract.max_quantity = 1000
        mock_contract.max_leverage = 150
        mock_contract.min_notional = 10

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_contract

        # Test
        result = validate_order_risk(
            symbol='BTCUSDT',
            quantity=0.001,
            price=50000,
            leverage=10,
            available_balance=10000
        )

        assert not result['valid']
        assert 'below minimum' in result['reason']

    @patch('broker.pi42.utils.risk_management.db_session')
    def test_validate_order_risk_success(self, mock_db):
        """Test successful order validation."""
        # Mock contract
        mock_contract = Mock()
        mock_contract.min_quantity = 0.001
        mock_contract.max_quantity = 1000
        mock_contract.max_leverage = 150
        mock_contract.min_notional = 10

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_contract

        # Test
        result = validate_order_risk(
            symbol='BTCUSDT',
            quantity=0.1,
            price=50000,
            leverage=10,
            available_balance=10000
        )

        assert result['valid']
        assert 'required_margin' in result
        assert 'notional_value' in result

    def test_check_position_health_critical(self):
        """Test position health check with critical risk."""
        health = check_position_health(
            entry_price=50000,
            current_price=46000,
            quantity=1.0,
            leverage=10,
            side='LONG',
            margin=5000
        )

        assert health['risk_level'] == 'CRITICAL'
        assert health['pnl'] < 0
        assert health['liquidation_distance_pct'] < 5


class TestOrderRouting:
    """Test smart order routing."""

    @patch('broker.pi42.utils.order_routing.db_session')
    @patch('broker.pi42.utils.order_routing.validate_order_risk')
    def test_route_order_success(self, mock_validate, mock_db):
        """Test successful order routing."""
        # Mock contract
        mock_contract = Mock()
        mock_contract.quantity_precision = 3
        mock_contract.price_precision = 2

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_contract

        # Mock validation
        mock_validate.return_value = {
            'valid': True,
            'required_margin': 500,
            'notional_value': 5000
        }

        # Test
        result = route_order(
            symbol='BTCUSDT',
            quantity=0.1,
            price=50000,
            order_type='LIMIT',
            side='BUY',
            available_balance=10000,
            leverage=10
        )

        assert result['status'] == 'success'
        assert 'routing_params' in result
        assert result['routing_params']['quantity'] == 0.1

    @patch('broker.pi42.utils.order_routing.db_session')
    def test_split_large_order(self, mock_db):
        """Test large order splitting."""
        # Mock contract
        mock_contract = Mock()
        mock_contract.max_quantity = 10
        mock_contract.quantity_precision = 3

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_contract

        # Test
        chunks = split_large_order('BTCUSDT', 25.0)

        assert len(chunks) == 3
        assert sum(chunks) == 25.0
        assert all(chunk <= 10 for chunk in chunks)

    @patch('broker.pi42.utils.order_routing.db_session')
    def test_optimize_order_execution_high_urgency(self, mock_db):
        """Test order optimization with high urgency."""
        # Mock contract
        mock_contract = Mock()
        mock_contract.max_quantity = 100

        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_contract

        # Test
        strategy = optimize_order_execution(
            symbol='BTCUSDT',
            quantity=10,
            side='BUY',
            urgency='HIGH'
        )

        assert strategy['order_type'] == 'MARKET'
        assert not strategy['split_order']

    def test_calculate_slippage_simple(self):
        """Test simple slippage estimation."""
        with patch('broker.pi42.utils.order_routing.db_session') as mock_db:
            # Mock contract
            mock_contract = Mock()
            mock_contract.max_quantity = 100

            mock_db.query.return_value.filter_by.return_value.first.return_value = mock_contract

            # Test
            result = calculate_slippage_estimate(
                symbol='BTCUSDT',
                quantity=10,
                side='BUY',
                current_price=50000
            )

            assert 'estimated_slippage_pct' in result
            assert result['method'] == 'simple'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
