"""Margin management API endpoints for crypto futures."""

from flask import request
from flask_restx import Namespace, Resource, fields
from database.auth_db import get_auth_token_broker
from limiter import limiter

api = Namespace('margin', description='Margin management operations')

add_margin_model = api.model('AddMargin', {
    'apikey': fields.String(required=True, description='API Key'),
    'symbol': fields.String(required=True, description='Trading symbol'),
    'amount': fields.Float(required=True, description='Margin amount to add'),
    'margin_asset': fields.String(required=False, description='USDT or INR', default='USDT')
})

reduce_margin_model = api.model('ReduceMargin', {
    'apikey': fields.String(required=True, description='API Key'),
    'symbol': fields.String(required=True, description='Trading symbol'),
    'amount': fields.Float(required=True, description='Margin amount to reduce')
})


@api.route('/addmargin')
class AddMargin(Resource):
    @limiter.limit("20 per minute")
    @api.doc(description='Add margin to crypto futures position')
    @api.expect(add_margin_model)
    def post(self):
        """Add margin to crypto futures position."""
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
                    'message': 'Margin management only available for crypto futures (Pi42)'
                }, 400

            # Validate required fields
            if 'symbol' not in data or 'amount' not in data:
                return {
                    'status': 'error',
                    'message': 'Symbol and amount are required'
                }, 400

            # Validate amount
            amount = float(data['amount'])
            if amount <= 0:
                return {
                    'status': 'error',
                    'message': 'Amount must be greater than 0'
                }, 400

            margin_asset = data.get('margin_asset', 'USDT')

            # Import and call Pi42 leverage API
            from broker.pi42.api.leverage_api import add_margin

            result, status_code = add_margin(
                data['symbol'],
                amount,
                auth_token
            )

            return result, status_code

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error adding margin: {str(e)}'
            }, 500


@api.route('/reducemargin')
class ReduceMargin(Resource):
    @limiter.limit("20 per minute")
    @api.doc(description='Reduce margin from crypto futures position')
    @api.expect(reduce_margin_model)
    def post(self):
        """Reduce margin from crypto futures position."""
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
                    'message': 'Margin management only available for crypto futures (Pi42)'
                }, 400

            # Validate required fields
            if 'symbol' not in data or 'amount' not in data:
                return {
                    'status': 'error',
                    'message': 'Symbol and amount are required'
                }, 400

            # Validate amount
            amount = float(data['amount'])
            if amount <= 0:
                return {
                    'status': 'error',
                    'message': 'Amount must be greater than 0'
                }, 400

            # Import and call Pi42 leverage API
            from broker.pi42.api.leverage_api import reduce_margin

            result, status_code = reduce_margin(
                data['symbol'],
                amount,
                auth_token
            )

            return result, status_code

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error reducing margin: {str(e)}'
            }, 500
