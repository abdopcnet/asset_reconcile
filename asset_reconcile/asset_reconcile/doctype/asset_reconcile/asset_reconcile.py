# Copyright (c) 2025, abdopcnet@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class AssetReconcile(Document):
    def validate(self):
        self.validate_items()
        self.calculate_totals()

    def validate_items(self):
        """Check for duplicate assets in the list"""
        assets_seen = set()
        for item in self.assets:
            if not item.asset:
                continue
            if item.asset in assets_seen:
                frappe.throw(
                    _("Asset {0} is duplicated in row {1}").format(
                        frappe.bold(item.asset), item.idx
                    )
                )
            assets_seen.add(item.asset)

    def calculate_totals(self):
        """Calculate system, physical, and variance values"""
        total_system = 0
        total_physical = 0

        for item in self.assets:
            if not item.asset:
                continue

            # Get asset value using ERPNext's proper method
            value_after_dep = flt(getattr(item, 'value_after_depreciation', 0))
            if not value_after_dep:
                asset_doc = frappe.get_cached_doc("Asset", item.asset)
                # Use ERPNext's get_value_after_depreciation method for accurate value
                if hasattr(asset_doc, 'get_value_after_depreciation'):
                    item.value_after_depreciation = asset_doc.get_value_after_depreciation()
                else:
                    item.value_after_depreciation = (
                        flt(asset_doc.value_after_depreciation)
                        or flt(asset_doc.gross_purchase_amount)
                    )
                item.gross_purchase_amount = flt(asset_doc.gross_purchase_amount)

            # Calculate values - use physical_qty (correct field name from JSON)
            physical_qty = flt(getattr(item, 'physical_qty', 0) or 0)
            system_qty = flt(item.system_quantity or 1)

            item.system_value = flt(item.value_after_depreciation) * system_qty
            item.physical_value = flt(item.value_after_depreciation) * physical_qty
            item.variance_value = flt(item.physical_value) - flt(item.system_value)
            item.variance = flt(physical_qty) - flt(system_qty)
            item.accumulated_depreciation = flt(item.gross_purchase_amount) - flt(
                item.value_after_depreciation
            )

            total_system += flt(item.system_value)
            total_physical += flt(item.physical_value)

        self.total_system_value = total_system
        self.total_physical_value = total_physical
        self.total_variance_value = total_physical - total_system


@frappe.whitelist()
def scan_asset_barcode(search_value, company=None, location=None):
    """Search Asset by barcode, name, or item barcode"""
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
            filters = {"item_code": item_barcode, "docstatus": 1}
            if company:
                filters["company"] = company
            if location:
                filters["location"] = location

            asset_name = frappe.db.get_value("Asset", filters, "name")

    if not asset_name:
        return {}

    # Get full asset data using ERPNext's proper methods
    return get_asset_data(asset_name, company, location)


def get_asset_data(asset_name, company=None, location=None):
    """Get asset data with proper value_after_depreciation calculation"""
    asset_doc = frappe.get_cached_doc("Asset", asset_name)

    # Validate company filter
    if company and asset_doc.company != company:
        return {}

    # Validate location filter
    if location and asset_doc.location != location:
        return {}

    # Use ERPNext's get_value_after_depreciation method for accurate value
    if hasattr(asset_doc, 'get_value_after_depreciation'):
        value_after_depreciation = asset_doc.get_value_after_depreciation()
    else:
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
    """Get all assets in a location for reconciliation"""
    return get_assets_by_filters(company=company, location=location)


@frappe.whitelist()
def get_assets_by_filters(company=None, location=None, asset_category=None, status=None):
    """Get all assets by filters for reconciliation
    If location is not provided, fetch all assets for the company
    Following ERPNext's Fixed Asset Register pattern
    """
    # Company is required
    if not company:
        frappe.throw(_("Company is required to fetch assets"))

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

        assets.append({
            "name": asset.name,
            "asset_name": asset.asset_name,
            "location": asset.location,
            "custodian": asset.custodian,
            "status": asset.status,
            "asset_category": asset.asset_category,
            "department": asset.department,
            "cost_center": asset.cost_center,
            "item_code": asset.item_code,
            "gross_purchase_amount": flt(asset.gross_purchase_amount),
            "value_after_depreciation": flt(asset.value_after_depreciation),
        })

    return assets
