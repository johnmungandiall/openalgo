"""Leverage management API endpoints for crypto futures."""

from flask import request
from flask_restx import Namespace, Resource, fields
from database.auth_db import get_auth_token_broker
from limiter import limiter

api = Namespace('leverage', description='Leverage management operations')

leverage_model = api.model('SetLeverage', {
    'apikey': fields.String(required=True, description='API Key'),
    'symbol': fields.String(required=True, description='Trading symbol'),
    'leverage': fields.Integer(required=True, description='Leverage (1-150)')
})


@api.route('/setleverage')
class SetLeverage(Resource):
    @limiter.limit("20 per minute")
    @api.doc(description='Set leverage for crypto futures symbol')
    @api.expect(leverage_model)
    def post(self):
        """Set leverage for crypto futures position."""
        try:
            data = request.json

            if not data or 'apikey' not in data:
                return {'status': 'error', 'message': 'API key required'}, 400

            # Get auth token and broker
            auth_token, broker = get_auth_token_broker(data['apikey'])

            if not auth_token:
                return {'status': 'error', 'message': 'Invalid API key'}, 401

            if broker != 'pi42':
                return {
                    'status': 'error',
                    'message': 'Leverage management only available for crypto futures (Pi42)'
                }, 400

            # Validate required fields
            if 'symbol' not in data or 'leverage' not in data:
                return {
                    'status': 'error',
                    'message': 'Symbol and leverage are required'
                }, 400

            # Validate leverage range
            leverage = int(data['leverage'])
            if not 1 <= leverage <= 150:
                return {
                    'status': 'error',
                    'message': 'Leverage must be between 1 and 150'
                }, 400

            # Import and call Pi42 leverage API
            from broker.pi42.api.leverage_api import change_leverage

            result, status_code = change_leverage(
                data['symbol'],
                leverage,
                auth_token
            )

            return result, status_code

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error setting leverage: {str(e)}'
            }, 500


@api.route('/getleverage')
class GetLeverage(Resource):
    @limiter.limit("60 per minute")
    @api.doc(description='Get current leverage for symbol')
    @api.param('apikey', 'API Key', required=True)
    @api.param('symbol', 'Trading symbol', required=True)
    def get(self):
        """Get current leverage for crypto futures symbol."""
        try:
            apikey = request.args.get('apikey')
            symbol = request.args.get('symbol')

            if not apikey or not symbol:
                return {
                    'status': 'error',
                    'message': 'API key and symbol are required'
                }, 400

            # Get auth token and broker
            auth_token, broker = get_auth_token_broker(apikey)

            if not auth_token:
                return {'status': 'error', 'message': 'Invalid API key'}, 401

            if broker != 'pi42':
                return {
                    'status': 'error',
                    'message': 'Leverage info only available for crypto futures (Pi42)'
                }, 400

            # Import and call Pi42 position API to get leverage
            from broker.pi42.api.position_api import get_positions

            positions, status_code = get_positions(auth_token)

            if status_code != 200:
                return positions, status_code

            # Find position for symbol
            for position in positions.get('data', []):
                if position['symbol'] == symbol:
                    return {
                        'status': 'success',
                        'data': {
                            'symbol': symbol,
                            'leverage': position['leverage'],
                            'margin_mode': position.get('margin_type', 'ISOLATED'),
                            'max_leverage': 150
                        }
                    }, 200

            # No position found, return default
            return {
                'status': 'success',
                'data': {
                    'symbol': symbol,
                    'leverage': 1,
                    'margin_mode': 'ISOLATED',
                    'max_leverage': 150
                }
            }, 200

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error getting leverage: {str(e)}'
            }, 500
