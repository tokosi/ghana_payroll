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
