# File Structure

```
asset_reconcile/
├── hooks.py
├── asset_reconcile/
│   ├── doctype/
│   │   ├── asset_reconcile/
│   │   │   ├── asset_reconcile.py
│   │   │   ├── asset_reconcile.js
│   │   │   └── asset_reconcile.json
│   │   └── asset_reconcile_item/
│   │       ├── asset_reconcile_item.py
│   │       └── asset_reconcile_item.json
│   ├── workspace/
│   │   └── asset_reconciliation/
│   │       └── asset_reconciliation.json
│   └── config/
└── templates/
    └── pages/
```

## Key Files

- `hooks.py` - App hooks configuration
- `asset_reconcile.py` - Main controller (validation, calculations, API methods)
- `asset_reconcile.js` - Form controller (barcode scanning, location fetch)
- `asset_reconcile_item.py` - Child table controller

