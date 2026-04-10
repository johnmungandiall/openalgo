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
    Calculate realized and unrealized PnL for a given Kotak position.
    Inspired by Flattrade's calculate_pnl pattern.

    Kotak doesn't provide rpnl/urmtom fields like Flattrade,
    so we calculate from buyAmt/sellAmt amounts.
    """
    # Calculate net quantity
    fl_buy_qty = safe_int(position.get("flBuyQty"))
    fl_sell_qty = safe_int(position.get("flSellQty"))
    cf_buy_qty = safe_int(position.get("cfBuyQty"))
    cf_sell_qty = safe_int(position.get("cfSellQty"))

    net_qty = (fl_buy_qty - fl_sell_qty) + (cf_buy_qty - cf_sell_qty)

    # Total amounts including carry-forward
    total_buy_amt = safe_float(position.get("buyAmt")) + safe_float(position.get("cfBuyAmt"))
    total_sell_amt = safe_float(position.get("sellAmt")) + safe_float(position.get("cfSellAmt"))

    # Realized P&L: for closed positions, it's simply sell - buy
    if net_qty == 0:
        realized_pnl = total_sell_amt - total_buy_amt
    else:
        # Open position - use rpnl if broker provides it
        realized_pnl = safe_float(position.get("rpnl"))

    # Unrealized P&L: will be calculated separately using LTP
    unrealized_pnl = 0.0

    return realized_pnl, unrealized_pnl, net_qty


def get_margin_data(auth_token):
    """
    Fetch and process margin and position data.
    Simplified following Flattrade's pattern.
    """
    try:
        # Parse auth token components
        access_token_parts = auth_token.split(":::")
        if len(access_token_parts) != 4:
            logger.error(
                f"Invalid auth token format. Expected 4 parts, got {len(access_token_parts)}"
            )
            return {}

        trading_token = access_token_parts[0]
        trading_sid = access_token_parts[1]
        base_url = access_token_parts[2]

        if not base_url:
            logger.error("Base URL not found in auth token")
            return {}

        # Get the shared httpx client
        client = get_httpx_client()

        # Fetch margin data
        payload = (
            "jData=%7B%22seg%22%3A%22ALL%22%2C%22exch%22%3A%22ALL%22%2C%22prod%22%3A%22ALL%22%7D"
        )
        headers = {
            "accept": "application/json",
            "Sid": trading_sid,
            "Auth": trading_token,
            "neo-fin-key": "neotradeapi",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = f"{base_url}/quick/user/limits"
        response = client.post(url, headers=headers, content=payload)
        margin_data = json.loads(response.text)

        if margin_data.get("stat") != "Ok":
            logger.error(f"Kotak Limits API error: {margin_data.get('emsg')}")
            return {}

        # Fetch position data (like Flattrade fetches PositionBook)
        from broker.kotak.api.order_api import get_positions

        positions_response = get_positions(auth_token)
        logger.debug(f"Positions response: {positions_response}")

        total_realised = 0.0
        total_unrealised = 0.0

        data = positions_response.get("data")
        if positions_response.get("stat", "").lower() == "ok" and data is not None:
            positions = data
            logger.info(f"Processing {len(positions)} positions for PnL")

            # Log first position fields for debugging
            if positions:
                logger.debug(f"Position fields: {list(positions[0].keys())}")

            # Collect symbols for batch LTP fetch (for unrealized P&L)
            symbols_to_fetch = []
            position_details = []

            for position in positions:
                realized_pnl, _, net_qty = calculate_pnl(position)
                total_realised += realized_pnl

                logger.debug(
                    f"Position {position.get('trdSym')}: net_qty={net_qty}, realized={realized_pnl:.2f}"
                )

                # Collect open positions for unrealized P&L calculation
                if net_qty != 0:
                    try:
                        from broker.kotak.mapping.transform_data import map_exchange
                        from database.token_db import get_symbol

                        oa_exchange = map_exchange(position.get("exSeg"))
                        token = position.get("tok")
                        oa_symbol = get_symbol(token, oa_exchange)

                        if oa_symbol and oa_exchange:
                            symbols_to_fetch.append({
                                "symbol": oa_symbol,
                                "exchange": oa_exchange
                            })
                            position_details.append({
                                "position": position,
                                "symbol": oa_symbol,
                                "exchange": oa_exchange,
                                "net_qty": net_qty,
                            })
                    except Exception as e:
                        logger.debug(f"Could not prepare symbol for LTP fetch: {e}")

            # Batch fetch LTP for unrealized P&L calculation
            if symbols_to_fetch:
                try:
                    from broker.kotak.api.data import BrokerData

                    broker_data = BrokerData(auth_token)
                    multiquotes_response = broker_data.get_multiquotes(symbols_to_fetch)

                    ltp_map = {}
                    for quote_item in multiquotes_response:
                        if "data" in quote_item and quote_item["data"]:
                            symbol = quote_item["symbol"]
                            exchange = quote_item["exchange"]
                            ltp = safe_float(quote_item["data"].get("ltp"))
                            if ltp > 0:
                                ltp_map[f"{symbol}_{exchange}"] = ltp

                    # Calculate unrealized P&L for each open position
                    for detail in position_details:
                        pos = detail["position"]
                        net_qty = detail["net_qty"]
                        key = f"{detail['symbol']}_{detail['exchange']}"
                        ltp = ltp_map.get(key, 0.0)

                        if ltp > 0:
                            # Calculate average price
                            total_buy_qty = safe_int(pos.get("flBuyQty")) + safe_int(pos.get("cfBuyQty"))
                            total_sell_qty = safe_int(pos.get("flSellQty")) + safe_int(pos.get("cfSellQty"))
                            total_buy_amt = safe_float(pos.get("buyAmt")) + safe_float(pos.get("cfBuyAmt"))
                            total_sell_amt = safe_float(pos.get("sellAmt")) + safe_float(pos.get("cfSellAmt"))

                            if net_qty > 0 and total_buy_qty > 0:
                                avg_price = total_buy_amt / total_buy_qty
                            elif net_qty < 0 and total_sell_qty > 0:
                                avg_price = total_sell_amt / total_sell_qty
                            else:
                                avg_price = 0

                            if avg_price > 0:
                                unrealized = (ltp - avg_price) * net_qty
                                total_unrealised += unrealized
                                logger.debug(
                                    f"Unrealized {pos.get('trdSym')}: qty={net_qty}, "
                                    f"avg={avg_price:.2f}, ltp={ltp:.2f}, unrealized={unrealized:.2f}"
                                )
                except Exception as e:
                    logger.warning(f"Could not fetch LTP for unrealized P&L: {e}")
                    # Fallback to API-provided unrealized P&L
                    total_unrealised = safe_float(margin_data.get('UnrealizedMtomPrsnt'))

        logger.info(f"PnL - Realized: {total_realised:.2f}, Unrealized: {total_unrealised:.2f}")

        # Calculate margin values
        collateral_value = safe_float(margin_data.get("CollateralValue"))
        pay_in = safe_float(margin_data.get("RmsPayInAmt"))
        pay_out = safe_float(margin_data.get("RmsPayOutAmt"))
        collateral = safe_float(margin_data.get("Collateral"))

        # Construct and return the processed margin data (standard format like Flattrade)
        processed_margin_data = {
            "availablecash": f"{collateral_value + pay_in - pay_out + collateral:.2f}",
            "collateral": f"{collateral:.2f}",
            "m2munrealized": f"{total_unrealised:.2f}",
            "m2mrealized": f"{total_realised:.2f}",
            "utiliseddebits": f"{safe_float(margin_data.get('MarginUsed')):.2f}",
        }

        logger.info(f"Margin data: {processed_margin_data}")
        return processed_margin_data

    except KeyError as e:
        logger.error(f"Missing expected field in margin data: {e}")
        return {}
    except httpx.HTTPError as e:
        logger.error(f"HTTP request failed: {e}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error fetching margin data: {e}")
        return {}
