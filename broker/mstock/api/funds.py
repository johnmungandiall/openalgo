import os

import httpx

from broker.mstock.api.data import BrokerData
from broker.mstock.api.order_api import get_positions
from broker.mstock.database import master_contract_db
from broker.mstock.mapping.order_data import (
    map_broker_exchange_to_openalgo,
    map_position_data,
)
from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)


def _to_float(value, default=0.0):
    """Coerce mStock string/None numeric fields to float."""
    if value in (None, "None", ""):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_pnl(entry, ltp=None):
    """Realised / unrealised P&L for a single mStock position.

    Mirrors flattrade's positions-based split. mStock's positions feed carries
    no per-leg realised/unrealised fields (no ``rpnl`` / ``urmtom``), so they are
    derived from ``netvalue`` plus the average cost of any open quantity, marking
    the open qty to live ``ltp`` exactly like flattrade's
    ``(lp - netavgprc) * netqty * prcftr`` formula.

    - ``netqty == 0`` (closed) → all of ``netvalue`` is **realised**.
    - ``netqty != 0`` (open) → ``unrealised = (ltp - avgnetprice) * netqty * mult``
      and ``realised = netvalue + avgnetprice * netqty * mult`` (the booked leg).
      This identity makes ``realised + unrealised`` equal the position's full
      mark-to-market P&L. When ``ltp`` is unavailable the open leg falls back to
      booked-only (``realised = netvalue``, ``unrealised = 0``).

    Args:
        entry: One raw mStock position dict.
        ltp: Live last-traded price for the position symbol, or ``None``.

    Returns:
        tuple[float, float]: ``(realized, unrealized)``.
    """
    netqty = _to_float(entry.get("netqty"))
    netvalue = _to_float(entry.get("netvalue"))
    avgnetprice = _to_float(entry.get("avgnetprice"))
    multiplier = _to_float(entry.get("multiplier"), 1.0) or 1.0

    if netqty == 0 or ltp is None:
        # Fully closed, or no live price to mark the open qty → booked only.
        return netvalue, 0.0

    unrealized = (ltp - avgnetprice) * netqty * multiplier
    realized = netvalue + avgnetprice * netqty * multiplier
    return realized, unrealized


def _compute_m2m_from_positions(auth_token):
    """Compute total realised / unrealised M2M from the positions feed.

    mStock's Type B ``fundsummary`` always returns ``REALISED_PROFITS`` and
    ``MTM_COMBINED`` as ``null``, so account-level M2M is never available there.
    Following flattrade, M2M is summed per position from ``/portfolio/positions``,
    fetching a live LTP for each *open* leg so its unrealised P&L is a true
    mark-to-market (see :func:`calculate_pnl`).

    Returns:
        tuple[float, float]: ``(m2mrealized, m2munrealized)``.
    """
    total_realized = 0.0
    total_unrealized = 0.0
    try:
        # map_position_data fills tradingsymbol (OpenAlgo format) from the
        # symboltoken and leaves the raw numeric fields intact.
        rows = map_position_data(get_positions(auth_token))
        if not rows:
            return total_realized, total_unrealized

        broker_data = None
        for position in rows:
            netqty = _to_float(position.get("netqty"))
            ltp = None

            if netqty != 0:
                # Open leg → fetch a live LTP to mark it to market.
                symbol = position.get("tradingsymbol")
                oa_exchange = map_broker_exchange_to_openalgo(
                    position.get("exchange", ""), position.get("instrumenttype", "")
                )
                if symbol and oa_exchange:
                    try:
                        if broker_data is None:
                            broker_data = BrokerData(auth_token)
                        quote = broker_data.get_quotes(symbol, oa_exchange)
                        ltp = _to_float(quote.get("ltp")) if quote else None
                        if not ltp:  # 0 or None → don't mark to a bogus price
                            ltp = None
                    except Exception:
                        logger.exception(
                            f"Failed to fetch LTP for open position {symbol} "
                            f"({oa_exchange}); falling back to booked P&L."
                        )
                        ltp = None

            realized, unrealized = calculate_pnl(position, ltp)
            total_realized += realized
            total_unrealized += unrealized
    except Exception:
        logger.exception("Error computing M2M from positions; defaulting to 0.")
        return 0.0, 0.0

    return total_realized, total_unrealized


def get_margin_data(auth_token):
    """Fetch margin (fund) data from MStock API using Type B authentication."""
    # Use BROKER_API_SECRET which contains the mStock API key
    api_key = os.getenv("BROKER_API_SECRET")

    if not api_key:
        logger.error("Missing environment variable: BROKER_API_SECRET")
        return {}

    logger.info(
        f"Fetching margin data with auth_token length: {len(auth_token) if auth_token else 0}"
    )
    logger.debug(f"Auth token (first 30 chars): {auth_token[:30] if auth_token else 'None'}...")
    logger.debug(f"API key length: {len(api_key) if api_key else 0}")

    headers = {
        "X-Mirae-Version": "1",
        "Authorization": f"Bearer {auth_token}",
        "X-PrivateKey": api_key,
    }

    try:
        client = get_httpx_client()
        response = client.get(
            "https://api.mstock.trade/openapi/typeb/user/fundsummary", headers=headers, timeout=10.0
        )
        logger.info(f"Fund summary API response status: {response.status_code}")

        response.raise_for_status()
        margin_data = response.json()

        logger.debug(
            f"Fund summary response: status={margin_data.get('status')}, has_data={bool(margin_data.get('data'))}"
        )
        logger.debug(f"Full margin data response: {margin_data}")
        if margin_data.get("status") == True and margin_data.get("data"):
            data = margin_data["data"][0]

            # Balance fields come straight from fundsummary. mStock's
            # REALISED_PROFITS / MTM_COMBINED are always null here, so M2M is
            # derived from the positions feed instead (see helper above).
            m2mrealized, m2munrealized = _compute_m2m_from_positions(auth_token)

            filtered_data = {
                "availablecash": f"{_to_float(data.get('AVAILABLE_BALANCE')):.2f}",
                "collateral": f"{_to_float(data.get('COLLATERALS')):.2f}",
                "m2mrealized": f"{m2mrealized:.2f}",
                "m2munrealized": f"{m2munrealized:.2f}",
                "utiliseddebits": f"{_to_float(data.get('AMOUNT_UTILIZED')):.2f}",
            }

            logger.debug(f"filteredMargin Data: {filtered_data}")
            return filtered_data

        logger.error(f"Margin API failed: {margin_data.get('message', 'No data')}")
        return {}

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error while fetching margin data: {e}")
        logger.error(f"Response status code: {e.response.status_code}")
        logger.error(f"Response body: {e.response.text}")
        try:
            error_detail = e.response.json()
            logger.error(f"Error details: {error_detail}")
        except Exception:
            pass
        return {}
    except httpx.RequestError as e:
        logger.error(f"Network Error while fetching margin data: {e}")
        return {}
    except Exception:
        logger.exception("Unexpected error while fetching margin data.")
        return {}
