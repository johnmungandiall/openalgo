"""Sync Pi42 contracts to database."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from broker.pi42.api.auth_api import Pi42Auth
from broker.pi42.database.master_contract_db import Pi42MasterContract


def main():
    """Sync Pi42 contracts."""
    # Get credentials
    api_key = os.getenv('PI42_API_KEY')
    api_secret = os.getenv('PI42_API_SECRET')

    if not api_key or not api_secret:
        print("Error: PI42_API_KEY and PI42_API_SECRET must be set in .env")
        return 1

    # Create auth and master contract instances
    auth = Pi42Auth(api_key, api_secret)
    master = Pi42MasterContract(auth)

    # Sync contracts
    try:
        result = master.sync_contracts()
        print(f"\n✓ Sync complete: {result['saved']}/{result['total']} contracts saved")
        return 0
    except Exception as e:
        print(f"\n✗ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
