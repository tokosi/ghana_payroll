// Copyright (c) 2026, Ghana Payroll Contributors
// License: MIT

frappe.pages["ghana-paye-calculator"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Ghana PAYE Calculator"),
		single_column: true,
	});

	new GhanaPayeCalculator(page);
};

class GhanaPayeCalculator {
	constructor(page) {
		this.page = page;
		this.currency = "GHS";
		this.make();
	}

	make() {
		this.page.main.html(`
			<div class="row">
				<div class="col-md-5">
					<div class="gh-calc-card">
						<h5 class="mb-3">${__("Monthly Earnings")}</h5>
						<div class="gh-inputs"></div>
						<button class="btn btn-primary btn-sm gh-calculate mt-3">${__("Calculate")}</button>
						<button class="btn btn-default btn-sm gh-reset mt-3">${__("Reset")}</button>
					</div>
				</div>
				<div class="col-md-7">
					<div class="gh-output"></div>
				</div>
			</div>
		`);

		const $inputs = this.page.main.find(".gh-inputs");
		this.fields = {};

		const definitions = [
			{ fieldname: "basic", label: __("Basic Salary"), description: __("SSNIT and Provident Fund are calculated on this.") },
			{ fieldname: "taxable_allowances", label: __("Taxable Allowances") },
			{ fieldname: "bonus", label: __("Bonus") },
			{ fieldname: "exempt_allowances", label: __("Tax Exempt Allowances") },
			{ fieldname: "relief", label: __("Personal Reliefs"), description: __("Approved monthly reliefs.") },
		];

		definitions.forEach((def) => {
			this.fields[def.fieldname] = frappe.ui.form.make_control({
				parent: $inputs,
				df: {
					fieldtype: "Currency",
					fieldname: def.fieldname,
					label: def.label,
					description: def.description,
					default: 0,
					change: () => this.calculate(),
				},
				render_input: true,
			});
			this.fields[def.fieldname].set_value(0);
		});

		this.page.main.find(".gh-calculate").on("click", () => this.calculate());
		this.page.main.find(".gh-reset").on("click", () => {
			Object.values(this.fields).forEach((f) => f.set_value(0));
			this.page.main.find(".gh-output").empty();
		});

		this.page.set_secondary_action(__("Settings"), () => {
			frappe.set_route("Form", "Ghana Payroll Settings");
		});
	}

	values() {
		const out = {};
		Object.keys(this.fields).forEach((k) => {
			out[k] = flt(this.fields[k].get_value()) || 0;
		});
		return out;
	}

	calculate() {
		const args = this.values();
		if (!args.basic && !args.taxable_allowances && !args.bonus) {
			this.page.main.find(".gh-output").empty();
			return;
		}

		frappe.call({
			method: "ghana_payroll.tax_engine.calculate",
			args: args,
			callback: (r) => {
				if (r.message) this.render(r.message);
			},
		});
	}

	render(res) {
		this.currency = res.currency || "GHS";
		const c = (v) => format_currency(v, this.currency);

		const bands = (res.breakdown || [])
			.map(
				(b) => `<tr>
					<td>${b.band} ${c(b.chargeable)}</td>
					<td>${b.rate}%</td>
					<td>${c(b.tax)}</td>
				</tr>`
			)
			.join("");

		const effective = res.gross ? ((res.total_paye / res.gross) * 100).toFixed(2) : "0.00";

		const warning = res.enabled
			? ""
			: `<div class="alert alert-warning py-2 px-3 mb-3">${__(
					"The Ghana PAYE engine is currently disabled, so Salary Slips will not use these figures."
			  )}</div>`;

		this.page.main.find(".gh-output").html(`
			${warning}
			<div class="gh-calc-card">
				<div class="row">
					<div class="col-4">
						<div class="gh-muted">${__("Gross Pay")}</div>
						<div class="gh-result-figure">${c(res.gross)}</div>
					</div>
					<div class="col-4">
						<div class="gh-muted">${__("Total PAYE")}</div>
						<div class="gh-result-figure text-danger">${c(res.total_paye)}</div>
					</div>
					<div class="col-4">
						<div class="gh-muted">${__("Net Pay")}</div>
						<div class="gh-result-figure text-success">${c(res.net_pay)}</div>
					</div>
				</div>
				<div class="gh-muted mt-2">${__("Effective tax rate on gross")}: <b>${effective}%</b></div>
			</div>

			<div class="gh-calc-card">
				<h6>${__("Chargeable Income")}</h6>
				<table class="gh-band-table">
					<tr><td>${__("Gross Pay")}</td><td>${c(res.gross)}</td></tr>
					<tr><td>${__("Less: Employee SSNIT")}</td><td>(${c(res.ssnit_employee)})</td></tr>
					<tr><td>${__("Less: Employee Provident Fund")}</td><td>(${c(res.pf_employee)})</td></tr>
					<tr><td>${__("Less: Tax Exempt Allowances")}</td><td>(${c(res.exempt_allowances)})</td></tr>
					<tr><td>${__("Less: Personal Reliefs")}</td><td>(${c(res.personal_relief)})</td></tr>
					<tr><td><b>${__("Chargeable Income")}</b></td><td><b>${c(res.chargeable_income)}</b></td></tr>
				</table>
			</div>

			<div class="gh-calc-card">
				<h6>${__("Graduated Bands")}</h6>
				<table class="gh-band-table">
					<thead><tr><th>${__("Band")}</th><th>${__("Rate")}</th><th>${__("Tax")}</th></tr></thead>
					<tbody>${bands || `<tr><td colspan="3">${__("No taxable income")}</td></tr>`}</tbody>
					<tfoot><tr><td colspan="2"><b>${__("Total PAYE")}</b></td><td><b>${c(res.total_paye)}</b></td></tr></tfoot>
				</table>
			</div>

			<div class="gh-calc-card">
				<h6>${__("Employer Obligations")}</h6>
				<table class="gh-band-table">
					<tr><td>${__("Employer SSNIT")}</td><td>${c(res.ssnit_employer)}</td></tr>
					<tr><td>${__("Employer Provident Fund")}</td><td>${c(res.pf_employer)}</td></tr>
					<tr><td>${__("Tier 1 / Tier 2 Split")}</td><td>${c(res.ssnit_tier1)} / ${c(res.ssnit_tier2)}</td></tr>
					<tr><td><b>${__("Total Cost to Company")}</b></td><td><b>${c(res.employer_cost)}</b></td></tr>
				</table>
			</div>
		`);
	}
}
