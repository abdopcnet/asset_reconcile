// Copyright (c) 2025, abdopcnet@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Reconcile', {
	setup(frm) {
		// Initialize barcode scanner
		frm.barcode_scanner = new erpnext.utils.BarcodeScanner({
			frm: frm,
			scan_api:
				'asset_reconcile.asset_reconcile.doctype.asset_reconcile.asset_reconcile.scan_asset_barcode',
			items_table_name: 'assets',
			qty_field: 'physical_qty',
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

				if (existing_row) {
					// Increment count if exists
					frappe.model.set_value(
						existing_row.doctype,
						existing_row.name,
						'physical_qty',
						flt(existing_row.physical_qty || 0) + 1,
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

				frappe.model.set_value(row.doctype, row.name, {
					asset: asset,
					asset_name: asset_name,
					location: location,
					asset_category: asset_category,
					item_code: item_code,
					system_quantity: 1,
					physical_qty: 1,
					variance: 0,
					// Set values from scan API response
					value_after_depreciation: data.value_after_depreciation || 0,
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

	onload(frm) {
		if (!frm.doc.reconciliation_date) {
			frm.set_value('reconciliation_date', frappe.datetime.get_today());
		}
		if (!frm.doc.reconciliation_time) {
			frm.set_value('reconciliation_time', frappe.datetime.now_time());
		}
		frm.set_value('counted_by', frappe.session.user);
		frm.set_df_property('counted_by', 'read_only', 1);
	},

	before_save(frm) {
		frm.set_value('counted_by', frappe.session.user);
	},

	scan_barcode(frm) {
		if (frm.barcode_scanner) {
			frm.barcode_scanner.process_scan();
		}
	},

	refresh(frm) {
		if (!frm.doc.counted_by) {
			frm.set_value('counted_by', frappe.session.user);
		}
		frm.set_df_property('counted_by', 'read_only', 1);
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Fetch Assets'), function () {
				frm.events.get_assets_from_location(frm);
			});
		}
	},

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
					frm.clear_table('assets');
					r.message.forEach(function (asset) {
						let row = frm.add_child('assets');
						row.asset = asset.name;
						row.asset_name = asset.asset_name;
						row.location = asset.location;
						row.asset_category = asset.asset_category;
						row.item_code = asset.item_code;
						row.system_quantity = 1;
						row.physical_qty = 1;
						// Set values from API response
						row.value_after_depreciation = asset.value_after_depreciation || 0;
						row.gross_purchase_amount = asset.gross_purchase_amount || 0;
					});
					frm.refresh_field('assets');
					frm.trigger('calculate_totals');
					frappe.show_alert({
						message: __('Fetched {0} assets', [r.message.length]),
						indicator: 'green',
					});
					console.log('[asset_reconcile.js] method: get_assets_from_location');
				} else {
					frappe.msgprint(__('No assets found'));
				}
			},
		});
	},

	calculate_totals(frm) {
		let total_system = 0;
		let total_physical = 0;

		(frm.doc.assets || []).forEach(function (row) {
			if (row.value_after_depreciation && row.system_quantity) {
				total_system += flt(row.value_after_depreciation) * flt(row.system_quantity);
			}
			if (row.value_after_depreciation && row.physical_qty) {
				total_physical += flt(row.value_after_depreciation) * flt(row.physical_qty);
			}
		});

		frm.set_value('total_system_value', total_system);
		frm.set_value('total_physical_value', total_physical);
		frm.set_value('total_variance_value', total_physical - total_system);
		console.log('[asset_reconcile.js] method: calculate_totals');
	},
});

frappe.ui.form.on('Asset Reconcile Item', {
	asset(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.asset) {
			// Use scan_asset_barcode API to get proper value_after_depreciation
			frappe.call({
				method: 'asset_reconcile.asset_reconcile.doctype.asset_reconcile.asset_reconcile.scan_asset_barcode',
				args: {
					search_value: row.asset,
					company: frm.doc.company,
				},
				callback: function (r) {
					if (r.message && r.message.asset) {
						let asset = r.message;
						frappe.model.set_value(cdt, cdn, {
							asset_name: asset.asset_name,
							location: asset.location,
							asset_category: asset.asset_category,
							item_code: asset.item_code,
							system_quantity: 1,
							physical_qty: 1,
							value_after_depreciation: asset.value_after_depreciation || 0,
							gross_purchase_amount: asset.gross_purchase_amount || 0,
						});
						frm.trigger('calculate_totals');
						console.log('[asset_reconcile.js] method: asset');
					}
				},
			});
		}
	},

	physical_qty(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.system_quantity) {
			frappe.model.set_value(
				cdt,
				cdn,
				'variance',
				flt(row.physical_qty || 0) - flt(row.system_quantity || 1),
			);
		}
		frm.trigger('calculate_totals');
		console.log('[asset_reconcile.js] method: physical_qty');
	},

	assets_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.system_quantity) {
			frappe.model.set_value(cdt, cdn, 'system_quantity', 1);
		}
		if (row.physical_qty === undefined || row.physical_qty === null) {
			frappe.model.set_value(cdt, cdn, 'physical_qty', 1);
		}
		console.log('[asset_reconcile.js] method: assets_add');
	},
});
