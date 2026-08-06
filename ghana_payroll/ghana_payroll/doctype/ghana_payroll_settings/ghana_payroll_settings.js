// Copyright (c) 2026, Ghana Payroll Contributors
// License: MIT

frappe.ui.form.on("Ghana Payroll Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Open PAYE Calculator"), () => {
			frappe.set_route("ghana-paye-calculator");
		});

		frm.add_custom_button(__("Reset Statutory Bands"), () => {
			frappe.confirm(
				__("Replace the current bands with the default GRA monthly schedule?"),
				() => {
					frappe.call({
						method: "ghana_payroll.ghana_payroll.doctype.ghana_payroll_settings.ghana_payroll_settings.reset_default_brackets",
						freeze: true,
						callback: () => {
							frappe.show_alert({ message: __("Statutory bands restored"), indicator: "green" });
							frm.reload_doc();
						},
					});
				}
			);
		});

		frm.add_custom_button(__("Create Income Tax Slab"), () => {
			frappe.prompt(
				[{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1 }],
				(values) => {
					frappe.call({
						method: "ghana_payroll.install.create_income_tax_slab",
						args: { company: values.company },
						freeze: true,
						callback: (r) => {
							if (r.message) {
								frappe.show_alert({
									message: __("Created {0}. Link it on Salary Structure Assignment.", [r.message]),
									indicator: "green",
								});
							} else {
								frappe.msgprint(__("Could not create the slab. Check the Error Log."));
							}
						},
					});
				},
				__("Placeholder Income Tax Slab"),
				__("Create")
			);
		}, __("Setup"));

		frm.add_custom_button(__("Map Component Accounts"), () => {
			frappe.prompt(
				[
					{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1 },
					{ fieldname: "ssnit_account", label: __("SSNIT Payable Account"), fieldtype: "Link", options: "Account" },
					{ fieldname: "pf_account", label: __("Provident Fund Payable Account"), fieldtype: "Link", options: "Account" },
					{ fieldname: "paye_account", label: __("PAYE Payable Account"), fieldtype: "Link", options: "Account" },
					{ fieldname: "hint", fieldtype: "HTML", options: "<p class='text-muted small'>Leave an account blank to create it under Duties and Taxes.</p>" },
				],
				(values) => {
					frappe.call({
						method: "ghana_payroll.install.setup_component_accounts",
						args: values,
						freeze: true,
						callback: (r) => {
							frappe.msgprint({
								title: __("Component Accounts"),
								indicator: (r.message || []).length ? "green" : "orange",
								message: (r.message || []).length
									? "<ul><li>" + r.message.join("</li><li>") + "</li></ul>"
									: __("Nothing was updated. Check the component mapping above."),
							});
						},
					});
				},
				__("Map Ghana Component Accounts"),
				__("Apply")
			);
		}, __("Setup"));

		frm.dashboard.clear_headline();
		if (!frm.doc.enabled) {
			frm.dashboard.set_headline(
				__("Ghana PAYE engine is <b>disabled</b>. Salary Slips will use the standard ERPNext annualised tax calculation.")
			);
		} else {
			const total = flt(frm.doc.ssnit_employee_rate) + flt(frm.doc.ssnit_employer_rate);
			frm.dashboard.set_headline(
				__("Ghana PAYE engine active &mdash; SSNIT {0}% total, Provident Fund {1}% employee / {2}% employer.", [
					total,
					flt(frm.doc.pf_employee_rate),
					flt(frm.doc.pf_employer_rate),
				])
			);
		}
	},

	enabled(frm) {
		frm.trigger("refresh");
	},
});
