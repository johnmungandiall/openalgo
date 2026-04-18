"""Contract information API endpoint for crypto futures."""

from flask import request
from flask_restx import Namespace, Resource
from database.auth_db import get_auth_token_broker
from limiter import limiter

api = Namespace('contract', description='Contract information operations')


@api.route('/contractinfo')
class ContractInfo(Resource):
    @limiter.limit("60 per minute")
    @api.doc(description='Get contract specifications for crypto futures')
    @api.param('apikey', 'API Key', required=True)
    @api.param('symbol', 'Trading symbol (optional, returns all if not provided)', required=False)
    def get(self):
        """Get contract specifications for crypto futures symbols."""
        try:
            apikey = request.args.get('apikey')
            symbol = request.args.get('symbol')

            if not apikey:
                return {'status': 'error', 'message': 'API key required'}, 400

            # Get auth token and broker
            auth_token, broker = get_auth_token_broker(apikey)

            if not auth_token:
                return {'status': 'error', 'message': 'Invalid API key'}, 401

            if broker != 'pi42':
                return {
                    'status': 'error',
                    'message': 'Contract info only available for crypto futures (Pi42)'
                }, 400

            # Import database functions
            from broker.pi42.database.master_contract_db import get_contract_info

            if symbol:
                # Get specific symbol
                contract = get_contract_info(symbol)
                if not contract:
                    return {
                        'status': 'error',
                        'message': f'Contract not found for symbol: {symbol}'
                    }, 404

                return {
                    'status': 'success',
                    'data': contract
                }, 200
            else:
                # Get all contracts
                from broker.pi42.database.master_contract_db import get_all_contracts

                contracts = get_all_contracts()

                return {
                    'status': 'success',
                    'data': contracts
                }, 200

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error getting contract info: {str(e)}'
            }, 500
