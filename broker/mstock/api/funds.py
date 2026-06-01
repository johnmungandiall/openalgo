import os

import httpx

from broker.mstock.api.order_api import get_positions
from broker.mstock.database import master_contract_db
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


def _compute_m2m_from_positions(auth_token):
    """Compute realised / unrealised M2M from the positions feed.

    mStock's Type B ``fundsummary`` always returns ``REALISED_PROFITS`` and
    ``MTM_COMBINED`` as ``null``, so account-level M2M is never available there.
    The positions endpoint, however, carries per-position P&L in ``netvalue``.
    We split it the same way the mStock web UI does:

    - ``netqty == 0`` → position is fully closed → P&L is **realised**.
    - ``netqty != 0`` → position still open → P&L is **unrealised** (M2M).

    Returns:
        tuple[float, float]: ``(m2mrealized, m2munrealized)``.
    """
    realized = 0.0
    unrealized = 0.0
    try:
        positions = get_positions(auth_token)
        rows = positions.get("data") if isinstance(positions, dict) else None
        if not isinstance(rows, list):
            return realized, unrealized

        for position in rows:
            netvalue = _to_float(position.get("netvalue"))
            netqty = int(_to_float(position.get("netqty")))
            if netqty == 0:
                realized += netvalue
            else:
                unrealized += netvalue
    except Exception:
        logger.exception("Error computing M2M from positions; defaulting to 0.")
        return 0.0, 0.0

    return realized, unrealized


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
