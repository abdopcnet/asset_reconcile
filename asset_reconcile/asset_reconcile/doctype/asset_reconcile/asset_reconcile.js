// Copyright (c) 2025, abdopcnet@gmail.com and contributors
// For license information, please see license.txt

/**
 * Client-side form events for Asset Reconcile main document
 * Handles barcode scanning, asset fetching, and totals calculation
 */
frappe.ui.form.on('Asset Reconcile', {
	/**
	 * Setup function: Called once when form is created
	 * Initializes barcode scanner for asset scanning
	 */
	setup(frm) {
		// Initialize barcode scanner for ERPNext
		frm.barcode_scanner = new erpnext.utils.BarcodeScanner({
			frm: frm,
			scan_api:
				'asset_reconcile.asset_reconcile.doctype.asset_reconcile.asset_reconcile.scan_asset_barcode',
			items_table_name: 'assets',
			qty_field: 'reconcile_qty',
			dont_allow_new_row: false,
			prompt_qty: false,
		});

		// Override scan_api_call to pass location parameter
		frm.barcode_scanner.scan_api_call = function (input, callback) {
			frappe
				.call({
					method: this.scan_api,
					args: {
						search_value: input,
						company: this.frm.doc.company,
						location: this.frm.doc.location,
					},
				})
				.then((r) => {
					callback(r);
				})
				.catch((err) => {
					callback({ message: {} });
				});
		};

		// Override update_table to work with Assets
		frm.barcode_scanner.update_table = function (data) {
			return new Promise((resolve, reject) => {
				let cur_grid = this.frm.fields_dict[this.items_table_name].grid;
				frappe.flags.trigger_from_barcode_scanner = true;

				const { asset, asset_name, location, asset_category, item_code } = data;

				if (!asset) {
					this.show_alert(__('Cannot find Asset with this Barcode'), 'red');
					this.clean_up();
					this.play_fail_sound();
					reject(new Error('Asset not found'));
					return;
				}

				// Check if asset already exists in table
				let existing_row = null;
				(this.frm.doc.assets || []).forEach(function (row) {
					if (row.asset === asset) {
						existing_row = row;
					}
				});

				// If asset exists, increment quantity
				if (existing_row) {
					frappe.model.set_value(
						existing_row.doctype,
						existing_row.name,
						'reconcile_qty',
						flt(existing_row.reconcile_qty || 0) + 1,
					);
					this.frm.trigger('calculate_totals');
					this.play_success_sound();
					resolve(existing_row);
					return;
				}

				// Add new row at the beginning (idx = 1)
				let row = frappe.model.add_child(
					this.frm.doc,
					cur_grid.doctype,
					this.items_table_name,
					1,
				);
				this.frm.script_manager.trigger(
					`${this.items_table_name}_add`,
					row.doctype,
					row.name,
				);

				// Set values from scan API response
				frappe.model.set_value(row.doctype, row.name, {
					asset: asset,
					asset_name: asset_name,
					location: location,
					asset_category: asset_category,
					item_code: item_code,
					system_qty: 1,
					reconcile_qty: 1,
					variance_qty: 0,
					variance_value: 0,
					system_value: data.value_after_depreciation || 0,
					reconcile_value: data.value_after_depreciation || 0,
					gross_purchase_amount: data.gross_purchase_amount || 0,
				});

				this.frm.refresh_field(this.items_table_name);
				this.frm.trigger('calculate_totals');
				this.play_success_sound();
				this.clean_up();
				resolve(row);
			});
		};
	},

	/**
	 * Onload event: Called when document is first loaded
	 * Sets default values for date, time, and counted_by fields
	 */
	onload(frm) {
		// Set default reconciliation date if not set
		if (!frm.doc.reconciliation_date) {
			frm.set_value('reconciliation_date', frappe.datetime.get_today());
		}
		// Set default reconciliation time if not set
		if (!frm.doc.reconciliation_time) {
			frm.set_value('reconciliation_time', frappe.datetime.now_time());
		}
		// Set current user as counted_by
		frm.set_value('counted_by', frappe.session.user);
		frm.set_df_property('counted_by', 'read_only', 1);
	},

	/**
	 * Before save event: Called before saving the document
	 * Ensures counted_by is set to current user
	 */
	before_save(frm) {
		frm.set_value('counted_by', frappe.session.user);
	},

	/**
	 * Event handler: When scan_barcode field changes
	 * Processes barcode scan input
	 */
	scan_barcode(frm) {
		if (frm.barcode_scanner) {
			frm.barcode_scanner.process_scan();
		}
	},

	/**
	 * Refresh event: Called every time form is refreshed
	 * Sets up UI elements and custom buttons
	 */
	refresh(frm) {
		// Ensure counted_by is set
		if (!frm.doc.counted_by) {
			frm.set_value('counted_by', frappe.session.user);
		}
		frm.set_df_property('counted_by', 'read_only', 1);

		// Style the 'get_assets' button to be green (success)
		// This mimics the 'success' style requested
		if (frm.fields_dict['get_assets'] && frm.fields_dict['get_assets'].$input) {
			frm.fields_dict['get_assets'].$input.addClass('btn-success');
			frm.fields_dict['get_assets'].$input.removeClass('btn-default'); // Optional: remove default style
		}
	},

	/**
	 * Event handler for the 'Get Assets' button
	 * Triggers the asset fetching logic
	 */
	get_assets(frm) {
		frm.events.get_assets_from_location(frm);
	},

	/**
	 * Trigger totals when rows are added/removed manually.
	 */
	assets_add(frm) {
		frm.trigger('calculate_totals');
	},

	assets_remove(frm) {
		frm.trigger('calculate_totals');
	},

	/**
	 * Fetches all assets from selected location and adds them to the table
	 * Groups assets by item_code and location, then calculates totals
	 */
	get_assets_from_location(frm) {
		// Company is required
		if (!frm.doc.company) {
			frappe.msgprint(__('Please select Company first'));
			return;
		}

		frappe.call({
			method: 'asset_reconcile.asset_reconcile.doctype.asset_reconcile.asset_reconcile.get_assets_by_filters',
			args: {
				company: frm.doc.company,
				location: frm.doc.location || '',
			},
			freeze: true,
			freeze_message: __('Fetching Assets...'),
			callback: function (r) {
				if (r.message && r.message.length) {
					// Add rows for each asset
					frm.clear_table('assets');

					// Python now returns the exact fields needed for the child table
					// We use direct assignment to avoid triggering field change events (event storm)
					// This is the most efficient, standard standard way for bulk loading
					r.message.forEach(function (row_data) {
						let row = frappe.model.add_child(
							frm.doc,
							'Asset Reconcile Item',
							'assets',
						);
						Object.assign(row, row_data);
					});

					frm.refresh_field('assets');
					frm.trigger('calculate_totals');
					frappe.show_alert({
						message: __('Fetched {0} assets', [r.message.length]),
						indicator: 'green',
					});
				} else {
					frappe.msgprint(__('No assets found'));
				}
			},
		});
	},

	/**
	 * Calculates totals for system value, reconcile value, and variance
	 * Sums up values from all rows in the assets table
	 */
	calculate_totals(frm) {
		let total_system_value = 0;
		let total_reconcile_value = 0;
		let total_system_qty = 0;
		let total_reconcile_qty = 0;

		// Sum up values from all rows
		(frm.doc.assets || []).forEach(function (row) {
			total_system_value += flt(row.system_value || 0);
			total_reconcile_value += flt(row.reconcile_value || 0);

			total_system_qty += flt(row.system_qty || 0);
			total_reconcile_qty += flt(row.reconcile_qty || 0);
		});

		// Update total fields
		frm.set_value('total_system_value', total_system_value);
		frm.set_value('total_reconcile_value', total_reconcile_value);
		frm.set_value('total_variance_value', total_reconcile_value - total_system_value);

		frm.set_value('total_system_qty', total_system_qty);
		frm.set_value('total_reconcile_qty', total_reconcile_qty);
		frm.set_value('total_variance_qty', total_reconcile_qty - total_system_qty);
	},
});

/**
 * Client-side form events for Asset Reconcile Item child table
 * Handles automatic data fetching when fields change in parent form context
 */
frappe.ui.form.on('Asset Reconcile Item', {
	/**
	 * Event handler: When asset changes in child table
	 * Fetches system data for the selected asset
	 */
	asset(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.asset && frm.doc.company) {
			frm.trigger('fetch_system_data', cdt, cdn);
		}
	},

	/**
	 * Event handler: When item_code changes in child table
	 * Fetches system data for the selected item
	 */
	item_code(frm, cdt, cdn) {
		// Only fetch if asset is not set, otherwise asset takes precedence
		let row = locals[cdt][cdn];
		if (!row.asset && row.item_code && frm.doc.company) {
			frm.trigger('fetch_system_data', cdt, cdn);
		}
	},

	/**
	 * Event handler: When location changes in child table
	 * Re-fetches system data if item_code is already selected
	 */
	location(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item_code && frm.doc.company) {
			frm.trigger('fetch_system_data', cdt, cdn);
		}
	},

	/**
	 * Fetches system data (quantity and value) from Asset records
	 * Based on asset, item_code, location, and company filters
	 * Automatically fills reconcile fields with system values (no variance initially)
	 */
	fetch_system_data(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		// If asset is cleared, clear other fields
		if (!row.asset && !row.item_code) {
			frappe.model.set_value(cdt, cdn, {
				system_qty: 0,
				system_value: 0,
				reconcile_qty: 0,
				reconcile_value: 0,
				variance_qty: 0,
				variance_value: 0,
				asset_name: '',
				asset_category: '',
			});
			return;
		}

		frappe.call({
			method: 'asset_reconcile.asset_reconcile.doctype.asset_reconcile.asset_reconcile.get_system_data',
			args: {
				asset: row.asset || '',
				item_code: row.item_code || '',
				location: row.location || '',
				company: frm.doc.company || '',
			},
			callback: function (r) {
				if (r.message && (r.message.quantity > 0 || r.message.value > 0)) {
					let system_qty_val = r.message.quantity || 0;
					let system_val = r.message.value || 0;

					// Update all fields: system fields and reconcile fields with same values
					// This ensures no variance initially (reconcile matches system)
					frappe.model.set_value(cdt, cdn, {
						system_qty: system_qty_val,
						system_value: system_val,
						asset_category: r.message.asset_category || '',
						reconcile_qty: system_qty_val, // Set reconcile_qty = system_qty
						reconcile_value: system_val, // Set reconcile_value = system_value
						variance_qty: 0, // No variance initially
						variance_value: 0, // No variance initially
					});

					// Trigger totals calculation in parent form
					if (frm.doctype === 'Asset Reconcile') {
						frm.trigger('calculate_totals');
					}
				} else {
					// Asset not found or no value in system?
					// Leave as is or warn? Default to 0?
					// If we picked an Asset that has no value, it might be 0.
				}
			},
		});
	},

	/**
	 * Event handler: When reconcile_qty (manual input quantity) changes
	 * Recalculates reconcile_value and variance automatically
	 */
	reconcile_qty(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		let reconcile_qty = flt(row.reconcile_qty || 0);
		// If system qty is 0 (new asset found?), we handle it
		let system_qty = flt(row.system_qty || 0);
		let system_value = flt(row.system_value || 0);

		// Calculate unit value from system data
		// If system_qty is 0 (unexpected overflow or new asset), unit value ?
		// If new asset found, system value is 0. So Reconcile Value = 0?
		// Unless we entered a value manually? But reconcile_value is Read Only.
		// So if system knows nothing, value is 0.
		let unit_value = 0;
		if (system_qty > 0) {
			unit_value = system_value / system_qty;
		}

		// Calculate reconcile_value
		let reconcile_value = reconcile_qty * unit_value;

		// Calculate variances
		let variance_qty = reconcile_qty - system_qty;
		let variance_value = reconcile_value - system_value;

		// Update all fields
		frappe.model.set_value(cdt, cdn, {
			reconcile_value: reconcile_value,
			variance_qty: variance_qty,
			variance_value: variance_value,
		});

		frm.trigger('calculate_totals');
	},
});
