"""Pi42 master contract database management."""

import requests
from typing import List, Dict, Optional
from sqlalchemy import text
from database.symbol import db_session, SymToken


class Pi42MasterContract:
    """Pi42 master contract management."""

    def __init__(self, auth):
        """Initialize with Pi42Auth instance."""
        self.auth = auth
        self.base_url = auth.base_url

    def download_contracts(self) -> List[Dict]:
        """
        Download all contract specifications from Pi42.

        Returns:
            List of contract dictionaries
        """
        # Use public API endpoint (no auth required)
        url = "https://api.pi42.com/v1/exchange/exchangeInfo"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to download contracts: {response.text}")

        data = response.json()
        # Pi42 returns contracts array with contract info
        return data.get('contracts', [])

    def process_contract(self, contract: Dict) -> Dict:
        """
        Process contract data into OpenAlgo format.

        Args:
            contract: Raw contract data from Pi42

        Returns:
            Processed contract dictionary
        """
        # Extract filters
        filters = {f['filterType']: f for f in contract.get('filters', [])}

        # Get quantity limits
        limit_qty = filters.get('LIMIT_QTY_SIZE', {})
        market_qty = filters.get('MARKET_QTY_SIZE', {})
        min_notional = filters.get('MIN_NOTIONAL', {})

        symbol = contract.get('name', '')

        return {
            'symbol': symbol,
            'brsymbol': symbol,
            'name': contract.get('contractName', symbol),
            'exchange': 'PI42',
            'brexchange': 'PI42',
            'token': symbol,
            'expiry': '',  # Perpetual contracts have no expiry
            'strike': 0.0,
            'lotsize': 1,
            'instrumenttype': 'FUTCOM',  # Futures Commodity
            'tick_size': 10 ** (-int(contract.get('pricePrecision', 0))),

            # Crypto-specific fields
            'broker_type': 'CRYPTO_futures',
            'min_quantity': float(limit_qty.get('minQty', 0.001)),
            'max_quantity': float(limit_qty.get('maxQty', 1000)),
            'price_precision': int(contract.get('pricePrecision', 0)),
            'quantity_precision': int(contract.get('quantityPrecision', 3)),
            'margin_assets': ','.join(contract.get('marginAssetsSupported', ['USDT'])),
            'max_leverage': int(contract.get('maxLeverage', 25)),
            'base_asset': contract.get('baseAsset', ''),
            'quote_asset': contract.get('quoteAsset', ''),
            'contract_type': contract.get('contractType', 'PERPETUAL'),
            'min_notional': float(min_notional.get('notional', 10)),
            'maintenance_margin_rate': float(contract.get('maintenanceMarginPercentage', 15)) / 100
        }

    def _get_precision(self, value: str) -> int:
        """
        Get decimal precision from tick/step size.

        Args:
            value: Tick or step size as string

        Returns:
            Number of decimal places
        """
        if '.' not in str(value):
            return 0
        return len(str(value).split('.')[1].rstrip('0'))

    def save_to_database(self, contracts: List[Dict]) -> int:
        """
        Save contracts to database.

        Args:
            contracts: List of processed contracts

        Returns:
            Number of contracts saved
        """
        saved_count = 0

        for contract in contracts:
            try:
                # Check if exists
                existing = db_session.query(SymToken).filter_by(
                    symbol=contract['symbol'],
                    exchange='PI42'
                ).first()

                if existing:
                    # Update existing
                    for key, value in contract.items():
                        setattr(existing, key, value)
                else:
                    # Create new
                    new_contract = SymToken(**contract)
                    db_session.add(new_contract)

                saved_count += 1
            except Exception as e:
                print(f"Error saving {contract['symbol']}: {e}")
                continue

        db_session.commit()
        return saved_count

    def sync_contracts(self) -> Dict:
        """
        Download and sync all contracts.

        Returns:
            Sync result dictionary
        """
        print("Downloading contracts from Pi42...")
        raw_contracts = self.download_contracts()

        print(f"Processing {len(raw_contracts)} contracts...")
        processed = [self.process_contract(c) for c in raw_contracts]

        print("Saving to database...")
        saved = self.save_to_database(processed)

        return {
            'total': len(raw_contracts),
            'saved': saved,
            'status': 'success'
        }


def get_contract_info(symbol: str) -> Optional[Dict]:
    """
    Get contract information for symbol.

    Args:
        symbol: Trading symbol

    Returns:
        Contract info dictionary or None
    """
    contract = db_session.query(SymToken).filter_by(
        symbol=symbol,
        exchange='PI42'
    ).first()

    if not contract:
        return None

    return {
        'symbol': contract.symbol,
        'base_asset': contract.base_asset,
        'quote_asset': contract.quote_asset,
        'min_quantity': contract.min_quantity,
        'max_quantity': contract.max_quantity,
        'price_precision': contract.price_precision,
        'quantity_precision': contract.quantity_precision,
        'tick_size': contract.tick_size,
        'max_leverage': contract.max_leverage,
        'margin_assets': contract.margin_assets.split(',') if contract.margin_assets else [],
        'min_notional': contract.min_notional
    }


def search_contracts(query: str, limit: int = 10) -> List[Dict]:
    """
    Search contracts by symbol or name.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching contracts
    """
    contracts = db_session.query(SymToken).filter(
        SymToken.exchange == 'PI42',
        SymToken.symbol.like(f'%{query.upper()}%')
    ).limit(limit).all()

    return [
        {
            'symbol': c.symbol,
            'name': c.name,
            'base_asset': c.base_asset,
            'quote_asset': c.quote_asset
        }
        for c in contracts
    ]
