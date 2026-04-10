# api/funds.py
import json

import httpx

from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)


def safe_float(value, default=0.0):
    """Convert value to float, handling None, empty strings, and invalid values."""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """Convert value to int, handling None, empty strings, and invalid values."""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def calculate_pnl(position):
    """
    Calculate realized and unrealized PnL for a given position.
    Following Flattrade's pattern: use broker-provided values with fallback calculation.
    """
    # Use broker-provided rpnl directly (includes all charges)
    realized_pnl = safe_float(position.get("rpnl"))

    # For unrealized P&L, we need to calculate from LTP
    # This will be done separately with batch LTP fetch
    unrealized_pnl = 0.0

    return realized_pnl, unrealized_pnl


def fetch_positions(auth_token):
    """Fetch position data from Kotak API."""
    from broker.kotak.api.order_api import get_positions

    positions_response = get_positions(auth_token)

    if positions_response.get("stat", "").lower() == "ok" and positions_response.get("data"):
        return positions_response["data"]

    return []


def get_margin_data(auth_token):
    """
    Fetch and process margin and position data.
    Simplified following Flattrade's pattern.
    """
    try:
        # Parse auth token components
        access_token_parts = auth_token.split(":::")
        if len(access_token_parts) != 4:
            logger.error(f"Invalid auth token format")
            return {}

        trading_token = access_token_parts[0]
        trading_sid = access_token_parts[1]
        base_url = access_token_parts[2]

        # Get the shared httpx client
        client = get_httpx_client()

        # Prepare payload for limits API
        payload = "jData=%7B%22seg%22%3A%22ALL%22%2C%22exch%22%3A%22ALL%22%2C%22prod%22%3A%22ALL%22%7D"

        headers = {
            "accept": "application/json",
            "Sid": trading_sid,
            "Auth": trading_token,
            "neo-fin-key": "neotradeapi",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Fetch margin data
        url = f"{base_url}/quick/user/limits"
        response = client.post(url, headers=headers, content=payload)
        margin_data = json.loads(response.text)

        # Check for API errors
        if margin_data.get("stat") != "Ok":
            logger.error(f"Kotak Limits API error: {margin_data.get('emsg')}")
            return {}

        # Fetch position data
        position_data = fetch_positions(auth_token)

        total_realised = 0.0
        total_unrealised = 0.0

        # Process position data (like Flattrade)
        if isinstance(position_data, list):
            for position in position_data:
                realized_pnl, unrealized_pnl = calculate_pnl(position)
                total_realised += realized_pnl

                # Calculate unrealized P&L for open positions
                fl_buy_qty = safe_int(position.get("flBuyQty"))
                fl_sell_qty = safe_int(position.get("flSellQty"))
                cf_buy_qty = safe_int(position.get("cfBuyQty"))
                cf_sell_qty = safe_int(position.get("cfSellQty"))

                net_qty = (fl_buy_qty - fl_sell_qty) + (cf_buy_qty - cf_sell_qty)

                # Only calculate unrealized for open positions
                if net_qty != 0:
                    # Get amounts for average price calculation
                    fl_buy_amt = safe_float(position.get("buyAmt"))
                    fl_sell_amt = safe_float(position.get("sellAmt"))
                    cf_buy_amt = safe_float(position.get("cfBuyAmt"))
                    cf_sell_amt = safe_float(position.get("cfSellAmt"))

                    total_buy_amt = fl_buy_amt + cf_buy_amt
                    total_sell_amt = fl_sell_amt + cf_sell_amt
                    total_buy_qty = fl_buy_qty + cf_buy_qty
                    total_sell_qty = fl_sell_qty + cf_sell_qty

                    # Calculate average price
                    if net_qty > 0 and total_buy_qty > 0:
                        avg_price = total_buy_amt / total_buy_qty
                    elif net_qty < 0 and total_sell_qty > 0:
                        avg_price = total_sell_amt / total_sell_qty
                    else:
                        avg_price = 0

                    # Get LTP (would need batch fetch in production)
                    ltp = safe_float(position.get("ltp"))

                    # Calculate unrealized P&L
                    if ltp > 0 and avg_price > 0:
                        unrealized_pnl = (ltp - avg_price) * net_qty
                        total_unrealised += unrealized_pnl

        # Calculate available cash
        collateral_value = safe_float(margin_data.get("CollateralValue"))
        pay_in = safe_float(margin_data.get("RmsPayInAmt"))
        pay_out = safe_float(margin_data.get("RmsPayOutAmt"))
        collateral = safe_float(margin_data.get("Collateral"))

        total_available_margin = collateral_value + pay_in - pay_out + collateral
        total_used_margin = safe_float(margin_data.get("MarginUsed"))

        # Format function for accounting style (negative values in parentheses)
        def format_value(value, use_accounting_format=True):
            """Format value with optional accounting format for negatives."""
            if use_accounting_format and value < 0:
                return f"({abs(value):.2f})"
            else:
                return f"{value:.2f}"

        # Construct and return the processed margin data
        processed_margin_data = {
            "availablecash": format_value(total_available_margin, False),
            "collateral": format_value(collateral, False),
            "m2munrealized": format_value(total_unrealised),
            "m2mrealized": format_value(total_realised),
            "utiliseddebits": format_value(total_used_margin, False),
        }

        logger.info(f"Successfully fetched margin data: {processed_margin_data}")
        return processed_margin_data

    except KeyError as e:
        logger.error(f"Missing expected field in margin data: {e}")
        return {}
    except httpx.HTTPError as e:
        logger.error(f"HTTP request failed while fetching margin data: {e}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse margin data JSON: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error fetching margin data: {e}")
        return {}
