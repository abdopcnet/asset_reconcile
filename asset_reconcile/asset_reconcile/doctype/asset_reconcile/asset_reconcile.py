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

            # Get asset value if not already fetched
            if not item.value_after_depreciation:
                asset_doc = frappe.get_cached_doc("Asset", item.asset)
                item.value_after_depreciation = (
                    asset_doc.value_after_depreciation or asset_doc.gross_purchase_amount
                )
                item.gross_purchase_amount = asset_doc.gross_purchase_amount

            # Calculate values
            item.system_value = flt(item.value_after_depreciation) * flt(
                item.system_quantity or 1
            )
            item.physical_value = flt(item.value_after_depreciation) * flt(
                item.physical_count or 0
            )
            item.variance_value = item.physical_value - item.system_value
            item.variance = flt(item.physical_count or 0) - \
                flt(item.system_quantity or 1)
            item.accumulated_depreciation = flt(item.gross_purchase_amount) - flt(
                item.value_after_depreciation
            )

            total_system += item.system_value
            total_physical += item.physical_value

        self.total_system_value = total_system
        self.total_physical_value = total_physical
        self.total_variance_value = total_physical - total_system


@frappe.whitelist()
def scan_asset_barcode(search_value, company=None, location=None):
    """Search Asset by barcode, name, or item barcode"""
    # 1. Search custom_barcode field in Asset (if exists)
    if frappe.db.has_column("Asset", "custom_barcode"):
        asset = frappe.db.get_value(
            "Asset",
            {"custom_barcode": search_value, "docstatus": 1},
            [
                "name",
                "asset_name",
                "location",
                "value_after_depreciation",
                "gross_purchase_amount",
                "custodian",
                "status",
                "asset_category",
                "department",
                "cost_center",
                "item_code",
            ],
            as_dict=True,
        )

        if asset:
            if company and frappe.db.get_value("Asset", asset.name, "company") != company:
                return {}
            if location and asset.location != location:
                return {}
            asset["asset"] = asset.name
            return asset

    # 2. Search Asset name directly
    asset = frappe.db.get_value(
        "Asset",
        {"name": search_value, "docstatus": 1},
        [
            "name",
            "asset_name",
            "location",
            "value_after_depreciation",
            "gross_purchase_amount",
            "custodian",
            "status",
            "asset_category",
            "department",
            "cost_center",
            "item_code",
        ],
        as_dict=True,
    )

    if asset:
        if company and frappe.db.get_value("Asset", asset.name, "company") != company:
            return {}
        asset["asset"] = asset.name
        return asset

    # 3. Search Item Barcode (if Item has barcode, find Asset by item_code)
    item_barcode = frappe.db.get_value(
        "Item Barcode",
        {"barcode": search_value},
        ["parent as item_code"],
        as_dict=True,
    )

    if item_barcode:
        filters = {"item_code": item_barcode.item_code, "docstatus": 1}
        if company:
            filters["company"] = company
        if location:
            filters["location"] = location

        asset = frappe.db.get_value(
            "Asset",
            filters,
            [
                "name",
                "asset_name",
                "location",
                "value_after_depreciation",
                "gross_purchase_amount",
                "custodian",
                "status",
                "asset_category",
                "department",
                "cost_center",
                "item_code",
            ],
            as_dict=True,
        )

        if asset:
            asset["asset"] = asset.name
            return asset

    return {}


@frappe.whitelist()
def get_assets_by_location(location, company=None):
    """Get all assets in a location for reconciliation"""
    filters = {"location": location, "docstatus": 1}
    if company:
        filters["company"] = company

    assets = frappe.get_all(
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
        ],
        order_by="asset_name",
    )

    return assets
