"""Funding rate API endpoints for crypto futures."""

from flask import request
from flask_restx import Namespace, Resource
from database.auth_db import get_auth_token_broker
from limiter import limiter

api = Namespace('funding', description='Funding rate operations')


@api.route('/fundingrate')
class FundingRate(Resource):
    @limiter.limit("60 per minute")
    @api.doc(description='Get current funding rate for symbol')
    @api.param('apikey', 'API Key', required=True)
    @api.param('symbol', 'Trading symbol', required=True)
    def get(self):
        """Get current funding rate for crypto futures symbol."""
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
                    'message': 'Funding rate only available for crypto futures (Pi42)'
                }, 400

            # Import and call Pi42 data API
            from broker.pi42.api.data import get_funding_rate

            result, status_code = get_funding_rate(symbol, auth_token)

            return result, status_code

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error getting funding rate: {str(e)}'
            }, 500


@api.route('/fundinghistory')
class FundingHistory(Resource):
    @limiter.limit("30 per minute")
    @api.doc(description='Get funding rate history for symbol')
    @api.param('apikey', 'API Key', required=True)
    @api.param('symbol', 'Trading symbol', required=True)
    @api.param('start_time', 'Start timestamp (ms)', required=False)
    @api.param('end_time', 'End timestamp (ms)', required=False)
    @api.param('limit', 'Number of records', default=100)
    def get(self):
        """Get funding rate history for crypto futures symbol."""
        try:
            apikey = request.args.get('apikey')
            symbol = request.args.get('symbol')
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            limit = int(request.args.get('limit', 100))

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
                    'message': 'Funding history only available for crypto futures (Pi42)'
                }, 400

            # Import and call Pi42 funds API
            from broker.pi42.api.funds_api import get_income_history

            # Get funding fee income history
            result, status_code = get_income_history(
                auth_token=auth_token,
                symbol=symbol,
                income_type='FUNDING_FEE',
                start_time=int(start_time) if start_time else None,
                end_time=int(end_time) if end_time else None,
                limit=limit
            )

            return result, status_code

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error getting funding history: {str(e)}'
            }, 500
