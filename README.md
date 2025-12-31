## Asset Reconcile

![Version](https://img.shields.io/badge/version-31.12.2025-blue)

Physical asset reconciliation app for ERPNext with barcode scanning support.

### Features

- **Physical Asset Counting** - Reconcile physical assets against system records
- **Barcode Scanning** - Fast asset identification via barcode scanner integration
- **Location-Based Fetch** - Auto-populate assets by location with one click
- **Variance Tracking** - Calculate and display system vs physical count differences
- **Real-Time Calculations** - Auto-calculate totals and variance values
- **Audit Trail** - Track who counted, when, and submission status
- **Submittable Document** - Full workflow with draft, submit, cancel, amend

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app asset_reconcile
```

### Quick Start

1. Navigate to **Asset Reconcile** DocType
2. Select Company and Location
3. Click **Fetch Assets from Location** or scan barcodes
4. Update physical counts
5. Review variance and submit

### License

MIT
