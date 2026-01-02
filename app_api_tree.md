# API Tree

## Document Methods

### Asset Reconcile

- `validate()` - Validate items (check duplicates), calculate totals
- `calculate_totals()` - Calculate system/physical/variance values
- `validate_items()` - Check for duplicate assets in table

## Whitelisted API Methods

### asset_reconcile.asset_reconcile.doctype.asset_reconcile.asset_reconcile

- `scan_asset_barcode(search_value, company=None, location=None)`
  - Description: Search Asset by barcode, name, or item barcode
  - Search order: custom_barcode → Asset name → Item barcode
  - Returns: Asset details (name, location, values, custodian, etc.)
  - Filters by company and location if provided

- `get_assets_by_location(location, company=None)`
  - Description: Get all assets in a location for reconciliation
  - Returns: List of assets with details
  - Filters by location and optional company

