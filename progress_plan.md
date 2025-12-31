# Asset Reconcile - Progress Plan

## Overview
Create Asset Reconcile DocType similar to Stock Reconciliation for physical asset counting with barcode support.

**App Location**: `/home/frappe/frappe-bench/apps/asset_reconcile`

---

## Step 1: Create Custom Field in Asset DocType

### Field Details
- **Fieldname**: `custom_barcode`
- **Label**: Barcode
- **Fieldtype**: Data
- **Insert After**: `asset_name` (or `location`)
- **Unique**: Yes (recommended)
- **In List View**: Yes
- **Search Index**: Yes

### How to Create
1. Go to: **Desk → Customize → Customize Form**
2. Select DocType: **Asset**
3. Click **Add Row** in fields section
4. Fill in the field details above
5. Save and **Reload DocType**

**OR** Use Python (after creating the field manually):
```python
# This is just for reference - field should be created via UI first
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

create_custom_field("Asset", {
    "fieldname": "custom_barcode",
    "label": "Barcode",
    "fieldtype": "Data",
    "insert_after": "asset_name",
    "unique": 1,
    "in_list_view": 1,
    "search_index": 1
})
```

---

## Step 2: Create Asset Reconcile Item (Child Table)

### DocType Details
- **Name**: `Asset Reconcile Item`
- **Module**: Asset Reconcile
- **Is Table**: Yes
- **Is Child Table**: Yes

### Fields to Create (in order)

#### Section 1: Asset Information
1. **asset** (Link)
   - Label: Asset
   - Options: Asset
   - Required: Yes
   - In List View: Yes
   - Columns: 3

2. **asset_name** (Data)
   - Label: Asset Name
   - Read Only: Yes
   - Fetch From: `asset.asset_name`
   - In List View: Yes
   - Columns: 3

3. **item_code** (Link)
   - Label: Item Code
   - Options: Item
   - Read Only: Yes
   - Fetch From: `asset.item_code`
   - Columns: 3

4. **item_name** (Data)
   - Label: Item Name
   - Read Only: Yes
   - Fetch From: `asset.item_name`
   - Columns: 3

5. **location** (Link)
   - Label: Location
   - Options: Location
   - Read Only: Yes
   - Fetch From: `asset.location`
   - In List View: Yes
   - Columns: 3

6. **custodian** (Link)
   - Label: Custodian
   - Options: Employee
   - Read Only: Yes
   - Fetch From: `asset.custodian`
   - Columns: 3

7. **status** (Data)
   - Label: Status
   - Read Only: Yes
   - Fetch From: `asset.status`
   - In List View: Yes
   - Columns: 2

8. **asset_category** (Link)
   - Label: Asset Category
   - Options: Asset Category
   - Read Only: Yes
   - Fetch From: `asset.asset_category`
   - Columns: 2

9. **department** (Link)
   - Label: Department
   - Options: Department
   - Read Only: Yes
   - Fetch From: `asset.department`
   - Columns: 2

10. **cost_center** (Link)
    - Label: Cost Center
    - Options: Cost Center
    - Read Only: Yes
    - Fetch From: `asset.cost_center`
    - Columns: 2

#### Section 2: Quantity
11. **Column Break** (Column Break)

12. **system_quantity** (Int)
    - Label: System Quantity
    - Read Only: Yes
    - Default: 1
    - In List View: Yes
    - Columns: 2

13. **physical_count** (Int)
    - Label: Physical Count
    - Default: 1
    - In List View: Yes
    - Columns: 2

14. **variance** (Int)
    - Label: Variance
    - Read Only: Yes
    - In List View: Yes
    - Columns: 2

#### Section 3: Values
15. **Section Break** (Section Break)
    - Label: Values

16. **gross_purchase_amount** (Currency)
    - Label: Gross Purchase Amount
    - Read Only: Yes
    - Fetch From: `asset.gross_purchase_amount`
    - Options: `Company:company:default_currency`
    - Columns: 2

17. **value_after_depreciation** (Currency)
    - Label: Value After Depreciation
    - Read Only: Yes
    - Fetch From: `asset.value_after_depreciation`
    - Options: `Company:company:default_currency`
    - In List View: Yes
    - Columns: 2

18. **accumulated_depreciation** (Currency)
    - Label: Accumulated Depreciation
    - Read Only: Yes
    - Options: `Company:company:default_currency`
    - Columns: 2

19. **system_value** (Currency)
    - Label: System Value
    - Read Only: Yes
    - Options: `Company:company:default_currency`
    - Columns: 2

20. **physical_value** (Currency)
    - Label: Physical Value
    - Read Only: Yes
    - Options: `Company:company:default_currency`
    - Columns: 2

21. **variance_value** (Currency)
    - Label: Variance Value
    - Read Only: Yes
    - Options: `Company:company:default_currency`
    - Columns: 2

22. **notes** (Small Text)
    - Label: Notes
    - Columns: 2

### How to Create
1. Go to: **Desk → Customize → New DocType**
2. Set **Is Child Table**: Yes
3. Add all fields above in order
4. Save DocType
5. **Reload DocType**

---

## Step 3: Create Asset Reconcile (Parent DocType)

### DocType Details
- **Name**: `Asset Reconcile`
- **Module**: Asset Reconcile
- **Is Submittable**: Yes
- **Naming Series**: `ACC-ASR-.YYYY.-`

### Fields to Create (in order)

#### Section 1: Basic Information
1. **naming_series** (Select)
   - Label: Series
   - Options: `ACC-ASR-.YYYY.-`
   - Required: Yes
   - Set Only Once: Yes
   - Print Hide: Yes

2. **company** (Link)
   - Label: Company
   - Options: Company
   - Required: Yes
   - Remember Last Selected Value: Yes
   - In List View: Yes

3. **Column Break** (Column Break)

4. **reconciliation_date** (Date)
   - Label: Reconciliation Date
   - Required: Yes
   - Default: Today
   - In List View: Yes

5. **reconciliation_time** (Time)
   - Label: Reconciliation Time
   - Required: Yes
   - Default: Now
   - In List View: Yes

6. **counted_by** (Link)
   - Label: Counted By
   - Options: User
   - Default: `__user__`

#### Section 2: Filters
7. **Section Break** (Section Break)
   - Label: Filters

8. **location** (Link)
   - Label: Location
   - Options: Location
   - Description: Filter assets by location

9. **set_location** (Link)
   - Label: Default Location
   - Options: Location
   - Description: Set default location for all items

#### Section 3: Barcode Scanning
10. **Section Break** (Section Break)
    - Label: Barcode Scanning

11. **scan_barcode** (Data)
    - Label: Scan Barcode
    - Options: Barcode
    - Description: Scan barcode to add asset

12. **scan_mode** (Check)
    - Label: Scan Mode
    - Default: 0
    - Description: Enable scan mode (disables auto-fetch)

#### Section 4: Assets Table
13. **Section Break** (Section Break)
    - Label: Assets

14. **assets** (Table)
    - Label: Assets
    - Options: Asset Reconcile Item
    - Required: Yes

#### Section 5: Totals
15. **Section Break** (Section Break)
    - Label: Totals

16. **total_system_value** (Currency)
    - Label: Total System Value
    - Read Only: Yes
    - Options: `Company:company:default_currency`

17. **Column Break** (Column Break)

18. **total_physical_value** (Currency)
    - Label: Total Physical Value
    - Read Only: Yes
    - Options: `Company:company:default_currency`

19. **total_variance_value** (Currency)
    - Label: Total Variance Value
    - Read Only: Yes
    - Options: `Company:company:default_currency`

20. **status** (Select)
    - Label: Status
    - Options: `\nDraft\nIn Progress\nCompleted\nCancelled`
    - Default: Draft

21. **amended_from** (Link)
    - Label: Amended From
    - Options: Asset Reconcile
    - Read Only: Yes
    - Print Hide: Yes
    - No Copy: Yes

### How to Create
1. Go to: **Desk → Customize → New DocType**
2. Set **Is Submittable**: Yes
3. Set **Naming Series**: `ACC-ASR-.YYYY.-`
4. Add all fields above in order
5. Set **Permissions** for appropriate roles
6. Save DocType
7. **Reload DocType**

---

## Step 4: Python Implementation

### File: `asset_reconcile/asset_reconcile/doctype/asset_reconcile/asset_reconcile.py`

**Key Methods to Implement**:
- `validate()`: Calculate totals, validate items
- `calculate_totals()`: Calculate system/physical/variance values
- `on_submit()`: Optional - update Asset records

**Whitelisted Functions**:
- `scan_asset_barcode(search_value, company=None, location=None)`: Search Asset by barcode
- `get_assets_by_location(location, company=None)`: Fetch assets by location

---

## Step 5: JavaScript Implementation

### File: `asset_reconcile/asset_reconcile/doctype/asset_reconcile/asset_reconcile.js`

**Key Features**:
- Initialize BarcodeScanner for Assets
- Handle `scan_barcode` field change
- Auto-populate Asset Reconcile Item on scan
- Calculate totals on field changes
- Fetch Assets by Location button

---

## Step 6: Testing Checklist

- [ ] Custom field `custom_barcode` created in Asset
- [ ] Asset Reconcile Item child table created
- [ ] Asset Reconcile parent DocType created
- [ ] Python controller implemented
- [ ] JavaScript controller implemented
- [ ] Barcode scanning works (custom_barcode, Asset name, Item barcode)
- [ ] Location-based asset fetching works
- [ ] Value calculations are correct
- [ ] Totals update automatically
- [ ] Submit/Cancel works correctly

---

## Notes

- All fields should be created manually via UI (Desk → Customize)
- Follow AGENTS.md rules for custom fields (custom_ prefix)
- Use same naming conventions as Stock Reconciliation
- Ensure proper permissions on new DocTypes
- Test thoroughly before production use

---

**Last Updated**: 2025-01-XX
**Status**: In Progress

