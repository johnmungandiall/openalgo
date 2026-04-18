"""Split Take Profit / Stop Loss API endpoint for crypto futures."""

from flask import request
from flask_restx import Namespace, Resource, fields
from database.auth_db import get_auth_token_broker
from limiter import limiter

api = Namespace('split_tpsl', description='Split TP/SL operations')

tp_sl_level_model = api.model('TPSLLevel', {
    'price': fields.Float(required=True, description='Price level'),
    'quantity': fields.Float(required=True, description='Quantity at this level')
})

split_tpsl_model = api.model('SplitTPSL', {
    'apikey': fields.String(required=True, description='API Key'),
    'symbol': fields.String(required=True, description='Trading symbol'),
    'tp_levels': fields.List(fields.Nested(tp_sl_level_model), description='Take profit levels'),
    'sl_levels': fields.List(fields.Nested(tp_sl_level_model), description='Stop loss levels')
})


@api.route('/splittakeprofit')
class SplitTakeProfit(Resource):
    @limiter.limit("20 per minute")
    @api.doc(description='Set split take profit and stop loss levels')
    @api.expect(split_tpsl_model)
    def post(self):
        """Set split take profit and stop loss levels for crypto futures position."""
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
                    'message': 'Split TP/SL only available for crypto futures (Pi42)'
                }, 400

            # Validate required fields
            if 'symbol' not in data:
                return {'status': 'error', 'message': 'Symbol is required'}, 400

            tp_levels = data.get('tp_levels', [])
            sl_levels = data.get('sl_levels', [])

            if not tp_levels and not sl_levels:
                return {
                    'status': 'error',
                    'message': 'At least one TP or SL level is required'
                }, 400

            # Get current position to determine side
            from broker.pi42.api.position_api import get_positions

            positions, status_code = get_positions(auth_token)
            if status_code != 200:
                return positions, status_code

            # Find position for symbol
            position = None
            for pos in positions.get('data', []):
                if pos['symbol'] == data['symbol']:
                    position = pos
                    break

            if not position:
                return {
                    'status': 'error',
                    'message': f'No open position found for {data["symbol"]}'
                }, 404

            # Determine opposite side for closing orders
            position_side = position['position_side']
            if position_side == 'LONG':
                close_side = 'SELL'
            else:
                close_side = 'BUY'

            # Import order API
            from broker.pi42.api.order_api import place_order

            tp_orders = []
            sl_orders = []

            # Place take profit orders
            for level in tp_levels:
                order_data = {
                    'symbol': data['symbol'],
                    'action': close_side,
                    'quantity': str(level['quantity']),
                    'price': str(level['price']),
                    'pricetype': 'LIMIT',
                    'product': 'ISOLATED',
                    'reduce_only': True
                }

                result, status = place_order(order_data, auth_token)
                if status == 200:
                    tp_orders.append(result.get('orderid'))

            # Place stop loss orders
            for level in sl_levels:
                order_data = {
                    'symbol': data['symbol'],
                    'action': close_side,
                    'quantity': str(level['quantity']),
                    'trigger_price': str(level['price']),
                    'pricetype': 'SL-M',
                    'product': 'ISOLATED',
                    'reduce_only': True
                }

                result, status = place_order(order_data, auth_token)
                if status == 200:
                    sl_orders.append(result.get('orderid'))

            return {
                'status': 'success',
                'message': f'Split TP/SL set successfully for {data["symbol"]}',
                'data': {
                    'symbol': data['symbol'],
                    'tp_orders': tp_orders,
                    'sl_orders': sl_orders,
                    'tp_levels_count': len(tp_orders),
                    'sl_levels_count': len(sl_orders)
                }
            }, 200

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error setting split TP/SL: {str(e)}'
            }, 500
