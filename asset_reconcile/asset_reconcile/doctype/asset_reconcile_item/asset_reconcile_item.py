# Copyright (c) 2025, abdopcnet@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class AssetReconcileItem(Document):
    """
    Document controller for Asset Reconcile Item child table.
    Logic is handled in the parent DocType (Asset Reconcile).
    """
    pass
