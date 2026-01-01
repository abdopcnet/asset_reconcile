# Workflow

## Asset Reconciliation Flow

```
1. Create Asset Reconcile
   ├─ Select Company
   ├─ Select Location
   └─ Save

2. Add Assets
   ├─ Option A: Fetch Assets by Location
   │   ├─ Click "Fetch Assets from Location"
   │   ├─ Auto-populate all assets in location
   │   └─ System quantity = 1 (default)
   │
   └─ Option B: Scan Barcode
       ├─ Use barcode scanner
       ├─ Search: custom_barcode → Asset name → Item barcode
       ├─ Auto-populate asset row
       └─ Repeat for each asset

3. Update Physical Counts
   ├─ For each asset row:
   │   ├─ Review system_quantity (from Asset)
   │   ├─ Enter physical_count (actual count)
   │   └─ Values auto-calculated:
   │       ├─ system_value = value_after_depreciation × system_quantity
   │       ├─ physical_value = value_after_depreciation × physical_count
   │       └─ variance_value = physical_value - system_value
   └─ Totals auto-calculated:
       ├─ total_system_value
       ├─ total_physical_value
       └─ total_variance_value

4. Validate
   ├─ Check for duplicate assets
   ├─ Recalculate totals
   └─ Save

5. Review Variance
   ├─ Check total_variance_value
   ├─ Review individual asset variances
   └─ Investigate discrepancies

6. Submit
   ├─ Submit document
   └─ Document becomes read-only (submitted state)
```

## Barcode Scanning Flow

```
User Scans Barcode
    ↓
scan_asset_barcode() Called
    ↓
Search Order:
    1. Asset.custom_barcode = search_value
    2. Asset.name = search_value
    3. Item Barcode → Find Asset by item_code
    ↓
Validate Company & Location (if provided)
    ↓
Return Asset Details
    ↓
Auto-populate Asset Reconcile Item Row
    ├─ Asset name
    ├─ Location
    ├─ Custodian
    ├─ Values
    └─ System quantity = 1
```

## Value Calculation Flow

```
Asset Added to Table
    ↓
calculate_totals() Triggered
    ↓
For Each Asset:
    ├─ Fetch value_after_depreciation (if missing)
    ├─ Calculate:
    │   ├─ system_value = value × system_quantity
    │   ├─ physical_value = value × physical_count
    │   ├─ variance_value = physical - system
    │   └─ variance = physical_count - system_quantity
    └─ Accumulate to totals
    ↓
Update Document Totals
```

