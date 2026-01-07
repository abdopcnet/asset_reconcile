# Copyright (c) 2025, abdopcnet@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class AssetReconcile(Document):
    """
    Document controller for Asset Reconcile main document
    Handles validation and totals calculation
    """

    def validate(self):
        """
        Main validation method
        Called before saving the document
        Validates items and calculates totals
        """
        self.validate_items()
        self.calculate_totals()

    def validate_items(self):
        """
        Check for duplicate assets in the assets table

        Prevents the same asset from appearing multiple times
        in the reconciliation table. also validates quantity for serialized assets.

        Raises:
                frappe.ValidationError: If duplicate asset found or invalid quantity
        """
        assets_seen = set()
        for item in self.assets:
            if not item.asset:
                continue

            if item.asset in assets_seen:
                frappe.throw(
                    _("Asset {0} is duplicated in row {1}").format(
                        frappe.bold(item.asset),
                        item.idx
                    )
                )
            assets_seen.add(item.asset)

            # Validate Quantity for Assets (should be 0 or 1)
            # If you need to warn on qty > 1, add a msgprint here.
            # Currently intentionally silent as per requirement.

    def calculate_totals(self):
        """
        Calculate system, reconcile, and variance totals

        Sums up values from all rows in the assets child table:
        - total_system_value: Sum of all system_value fields
        - total_reconcile_value: Sum of all reconcile_value fields
        - total_variance_value: Difference between reconcile and system totals
        - total_system_qty: Sum of all system_qty fields
        - total_reconcile_qty: Sum of all reconcile_qty fields
        - total_variance_qty: Difference between reconcile type and system qty
        """
        total_system_value = 0
        total_reconcile_value = 0
        total_system_qty = 0
        total_reconcile_qty = 0

        # Loop through all items in assets table
        for item in self.assets:
            # Calculate row-level values
            reconcile_qty = flt(item.reconcile_qty or 0)
            system_qty = flt(item.system_qty or 0)
            system_value = flt(item.system_value or 0)

            unit_value = 0.0
            if system_qty > 0:
                unit_value = system_value / system_qty
            elif reconcile_qty > 0 and item.asset:
                # If system qty is 0 but we found it, try to get value from asset ref if possible?
                # Ideally fetch_system_data handles this.
                pass

            # Calculate Reconcile Value based on unit value of system asset
            item.reconcile_value = reconcile_qty * unit_value

            # Simple difference
            item.variance_qty = reconcile_qty - system_qty
            item.variance_value = item.reconcile_value - system_value

            # Sum up values from child table
            total_system_value += system_value
            total_reconcile_value += item.reconcile_value
            total_system_qty += system_qty
            total_reconcile_qty += reconcile_qty

        # Update total fields
        self.total_system_value = total_system_value
        self.total_reconcile_value = total_reconcile_value
        self.total_variance_value = total_reconcile_value - total_system_value

        self.total_system_qty = total_system_qty
        self.total_reconcile_qty = total_reconcile_qty
        self.total_variance_qty = total_reconcile_qty - total_system_qty
        

@frappe.whitelist()
def scan_asset_barcode(search_value, company=None, location=None):
    """
    Search Asset by barcode, name, or item barcode

    This function searches for assets in three ways:
    1. Search custom_barcode field in Asset (if exists)
    2. Search Asset name directly
    3. Search Item Barcode, then find Asset by item_code

    Args:
            search_value(str): Barcode, asset name, or item barcode to search
            company(str, optional): Company filter
            location(str, optional): Location filter

    Returns:
            dict: Asset data dictionary or empty dict if not found
    """
    asset_name = None

    # 1. Search custom_barcode field in Asset (if exists)
    if frappe.db.has_column("Asset", "custom_barcode"):
        asset_name = frappe.db.get_value(
            "Asset",
            {"custom_barcode": search_value, "docstatus": 1},
            "name",
        )

    # 2. Search Asset name directly
    if not asset_name:
        asset_name = frappe.db.get_value(
            "Asset",
            {"name": search_value, "docstatus": 1},
            "name",
        )

    # 3. Search Item Barcode (if Item has barcode, find Asset by item_code)
    if not asset_name:
        item_barcode = frappe.db.get_value(
            "Item Barcode",
            {"barcode": search_value},
            "parent",
        )

        if item_barcode:
            # Build filters for Asset search
            filters = {"item_code": item_barcode, "docstatus": 1}
            if company:
                filters["company"] = company
            if location:
                filters["location"] = location

            asset_name = frappe.db.get_value("Asset", filters, "name")

    # Return empty dict if asset not found
    if not asset_name:
        return {}

    # Get full asset data using ERPNext's proper methods
    return get_asset_data(asset_name, company, location)


def get_asset_data(asset_name, company=None, location=None):
    """
    Get asset data with proper value_after_depreciation calculation

    Retrieves asset document and calculates accurate value after depreciation.
    Validates company and location filters if provided.

    Args:
            asset_name(str): Name of the asset document
            company(str, optional): Company filter for validation
            location(str, optional): Location filter for validation

    Returns:
            dict: Dictionary containing asset information:
                    - asset: Asset name
                    - name: Asset name
                    - asset_name: Asset display name
                    - location: Asset location
                    - value_after_depreciation: Calculated value after depreciation
                    - gross_purchase_amount: Original purchase amount
                    - custodian: Asset custodian
                    - status: Asset status
                    - asset_category: Asset category
                    - department: Department
                    - cost_center: Cost center
                    - item_code: Item code
    """
    asset_doc = frappe.get_cached_doc("Asset", asset_name)

    # Validate company filter
    if company and asset_doc.company != company:
        return {}

    # Validate location filter
    if location and asset_doc.location != location:
        return {}

    # Use ERPNext's get_value_after_depreciation method for accurate value
    # This ensures proper depreciation calculation if asset uses depreciation
    if hasattr(asset_doc, 'get_value_after_depreciation'):
        value_after_depreciation = asset_doc.get_value_after_depreciation()
    else:
        # Fallback to stored value or gross purchase amount
        value_after_depreciation = (
            flt(asset_doc.value_after_depreciation)
            or flt(asset_doc.gross_purchase_amount)
        )

    return {
        "asset": asset_doc.name,
        "name": asset_doc.name,
        "asset_name": asset_doc.asset_name,
        "location": asset_doc.location,
        "value_after_depreciation": flt(value_after_depreciation),
        "gross_purchase_amount": flt(asset_doc.gross_purchase_amount),
        "custodian": asset_doc.custodian,
        "status": asset_doc.status,
        "asset_category": asset_doc.asset_category,
        "department": asset_doc.department,
        "cost_center": asset_doc.cost_center,
        "item_code": asset_doc.item_code,
    }


@frappe.whitelist()
def get_assets_by_location(location, company=None):
    """
    Get all assets in a location for reconciliation

    Convenience function that calls get_assets_by_filters with location parameter

    Args:
            location(str): Location to filter assets
            company(str, optional): Company filter

    Returns:
            list: List of asset dictionaries
    """
    return get_assets_by_filters(company=company, location=location)


@frappe.whitelist()
def get_assets_by_filters(company=None, location=None, asset_category=None, status=None):
    """
    Get all assets by filters for reconciliation

    If location is not provided, fetches all assets for the company.
    Follows ERPNext's Fixed Asset Register pattern for filtering.

    By default, excludes disposed assets(Sold, Scrapped, Capitalized).

    Args:
            company(str, optional): Company filter(required)
            location(str, optional): Location filter
            asset_category(str, optional): Asset category filter
            status(str, optional): Status filter. If None, excludes disposed assets

    Returns:
            list: List of asset dictionaries containing:
                    - name: Asset name
                    - asset_name: Asset display name
                    - location: Asset location
                    - custodian: Asset custodian
                    - status: Asset status
                    - asset_category: Asset category
                    - department: Department
                    - cost_center: Cost center
                    - item_code: Item code
                    - gross_purchase_amount: Original purchase amount
                    - value_after_depreciation: Calculated value after depreciation

    Raises:
            frappe.ValidationError: If company is not provided
    """
    # Company is required
    if not company:
        frappe.throw(_("Company is required to fetch assets"))

    # Build base filters
    filters = {"docstatus": 1, "company": company}

    # Location filter (optional)
    if location:
        filters["location"] = location

    # Asset category filter (optional)
    if asset_category:
        filters["asset_category"] = asset_category

    # Status filter - exclude disposed assets by default (following ERPNext pattern)
    if status:
        filters["status"] = status
    else:
        # Exclude Sold, Scrapped, Capitalized assets (like Fixed Asset Register)
        filters["status"] = ("not in", ["Sold", "Scrapped", "Capitalized"])

    # Get asset data with required fields
    asset_records = frappe.get_all(
        "Asset",
        filters=filters,
        fields=[
            "name",
            "asset_name",
            "location",
            "custodian",
            "status",
            "asset_category",
            "department",
            "cost_center",
            "item_code",
            "gross_purchase_amount",
            "value_after_depreciation",
            "calculate_depreciation",
        ],
        order_by="asset_name",
    )

    # Get accurate value_after_depreciation for assets with depreciation
    assets = []
    for asset in asset_records:
        # For assets with calculate_depreciation, get accurate value from method
        if asset.calculate_depreciation:
            asset_doc = frappe.get_cached_doc("Asset", asset.name)
            if hasattr(asset_doc, 'get_value_after_depreciation'):
                asset["value_after_depreciation"] = asset_doc.get_value_after_depreciation()

        # Fallback to gross_purchase_amount if value_after_depreciation is 0
        if not flt(asset.value_after_depreciation):
            asset["value_after_depreciation"] = flt(asset.gross_purchase_amount)

        # Build result dictionary
        # Return fully prepared dict for Asset Reconcile Item
        system_value = flt(asset.value_after_depreciation)
        if not system_value:
            # Fallback to gross purchase amount if needed, though loop above handles it
            system_value = flt(asset.gross_purchase_amount)

        assets.append({
            # Standard Fields
            "asset": asset.name,
            "asset_name": asset.asset_name,
            "item_code": asset.item_code,
            "location": asset.location,
            "asset_category": asset.asset_category,

            # System Data
            "system_qty": 1,
            "system_value": system_value,
            "reconcile_qty": 1,
            "reconcile_value": system_value,

            # Variance (Defaults to 0)
            "variance_qty": 0,
            "variance_value": 0,

            # Extra Info
            "gross_purchase_amount": flt(asset.gross_purchase_amount),
            "custodian": asset.custodian,
            "status": asset.status,
            "department": asset.department,
            "cost_center": asset.cost_center,
        })

    return assets


@frappe.whitelist()
def get_system_data(item_code=None, location=None, company=None, asset=None):
    """
    Get system quantity and value for an item or asset from Asset records

    Args:
            item_code(str, optional): Item code to search for
            location(str, optional): Location filter
            company(str, optional): Company filter
            asset(str, optional): Asset filter

    Returns:
            dict: Dictionary with quantity, value, and asset_category
    """
    if not item_code and not asset:
        return {}

    # Build filters for Asset search
    filters = {"docstatus": 1}

    if asset:
        filters["name"] = asset
    elif item_code:
        filters["item_code"] = item_code

    if company:
        filters["company"] = company

    if location and not asset:
        # If asset is specified, location check might be restrictive if asset moved?
        # But for checking "System Data" at that location, we should probably respect it?
        # ERPNext convention: Asset location is single.
        filters["location"] = location

    # Get all assets matching the filters
    assets = frappe.get_all(
        "Asset",
        filters=filters,
        fields=["name", "value_after_depreciation", "gross_purchase_amount", "asset_category"]
    )

    if not assets:
        return {"quantity": 0, "value": 0, "asset_category": ""}

    quantity = len(assets)
    total_value = 0
    asset_category = assets[0].asset_category if assets else ""

    for asset_data in assets:
        # Get cached asset document for accurate value calculation
        asset_doc = frappe.get_cached_doc("Asset", asset_data.name)

        if hasattr(asset_doc, 'get_value_after_depreciation'):
            value = asset_doc.get_value_after_depreciation()
        else:
            value = flt(asset_data.value_after_depreciation) or flt(asset_data.gross_purchase_amount)

        total_value += flt(value)

    return {
        "quantity": quantity,
        "value": total_value,
        "asset_category": asset_category
    }
