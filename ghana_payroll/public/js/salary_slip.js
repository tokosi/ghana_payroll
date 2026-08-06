// Copyright (c) 2026, Ghana Payroll Contributors
// License: MIT

frappe.ui.form.on("Salary Slip", {
	refresh(frm) {
		if (!frm.doc.gh_chargeable_income && !frm.doc.gh_total_paye) return;

		const currency = frm.doc.currency || "GHS";
		frm.dashboard.add_indicator(
			__("Chargeable Income: {0}", [format_currency(frm.doc.gh_chargeable_income, currency)]),
			"blue"
		);
		frm.dashboard.add_indicator(
			__("PAYE: {0}", [format_currency(frm.doc.gh_total_paye, currency)]),
			"orange"
		);

		let bands = [];
		try {
			bands = JSON.parse(frm.doc.gh_paye_breakdown || "[]");
		} catch (e) {
			bands = [];
		}
		if (!bands.length) return;

		frm.add_custom_button(__("PAYE Band Breakdown"), () => {
			const rows = bands
				.map(
					(b) => `<tr>
						<td>${b.band} ${format_currency(b.chargeable, currency)}</td>
						<td>${b.rate}%</td>
						<td>${format_currency(b.tax, currency)}</td>
					</tr>`
				)
				.join("");

			frappe.msgprint({
				title: __("Ghana PAYE Computation"),
				indicator: "blue",
				message: `<table class="table table-bordered gh-band-table">
					<thead><tr><th>${__("Band")}</th><th>${__("Rate")}</th><th>${__("Tax")}</th></tr></thead>
					<tbody>${rows}</tbody>
					<tfoot><tr><td colspan="2"><b>${__("Total PAYE")}</b></td>
					<td><b>${format_currency(frm.doc.gh_total_paye, currency)}</b></td></tr></tfoot>
				</table>`,
			});
		});
	},
});
