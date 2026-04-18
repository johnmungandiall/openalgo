"""Liquidation price calculator API endpoint for crypto futures."""

from flask import request
from flask_restx import Namespace, Resource, fields
from database.auth_db import get_auth_token_broker
from limiter import limiter

api = Namespace('liquidation', description='Liquidation price calculator')

liquidation_model = api.model('LiquidationPrice', {
    'apikey': fields.String(required=True, description='API Key'),
    'symbol': fields.String(required=True, description='Trading symbol'),
    'entry_price': fields.Float(required=True, description='Entry price'),
    'quantity': fields.Float(required=True, description='Position quantity'),
    'leverage': fields.Integer(required=True, description='Leverage'),
    'side': fields.String(required=True, description='LONG or SHORT')
})


@api.route('/liquidationprice')
class LiquidationPrice(Resource):
    @limiter.limit("60 per minute")
    @api.doc(description='Calculate liquidation price for position')
    @api.expect(liquidation_model)
    def post(self):
        """Calculate liquidation price for crypto futures position."""
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
                    'message': 'Liquidation calculator only available for crypto futures (Pi42)'
                }, 400

            # Validate required fields
            required_fields = ['symbol', 'entry_price', 'quantity', 'leverage', 'side']
            for field in required_fields:
                if field not in data:
                    return {
                        'status': 'error',
                        'message': f'{field} is required'
                    }, 400

            # Validate side
            side = data['side'].upper()
            if side not in ['LONG', 'SHORT']:
                return {
                    'status': 'error',
                    'message': 'Side must be LONG or SHORT'
                }, 400

            # Import risk management utilities
            from broker.pi42.utils.risk_management import calculate_liquidation_price

            entry_price = float(data['entry_price'])
            leverage = int(data['leverage'])
            maintenance_margin_rate = 0.005  # 0.5% default

            # Calculate liquidation price
            liquidation_price = calculate_liquidation_price(
                entry_price=entry_price,
                leverage=leverage,
                side=side,
                maintenance_margin_rate=maintenance_margin_rate
            )

            # Calculate distance percentage
            if side == 'LONG':
                distance_pct = ((entry_price - liquidation_price) / entry_price) * 100
            else:
                distance_pct = ((liquidation_price - entry_price) / entry_price) * 100

            # Determine risk level
            if distance_pct > 20:
                risk_level = 'low'
            elif distance_pct > 10:
                risk_level = 'medium'
            elif distance_pct > 5:
                risk_level = 'high'
            else:
                risk_level = 'critical'

            return {
                'status': 'success',
                'data': {
                    'symbol': data['symbol'],
                    'entry_price': entry_price,
                    'liquidation_price': round(liquidation_price, 2),
                    'distance_percentage': round(distance_pct, 2),
                    'risk_level': risk_level,
                    'leverage': leverage,
                    'side': side
                }
            }, 200

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error calculating liquidation price: {str(e)}'
            }, 500
