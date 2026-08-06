# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""Ghana Payroll Summary: full cost-to-company view for the period."""

from frappe import _

from ghana_payroll.report_utils import (
	currency_column,
	currency_field,
	employee_columns,
	get_salary_slips,
)


def execute(filters=None):
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data), get_summary(data)


def get_columns():
	return (
		employee_columns()
		+ [
			{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
			{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 140},
			{"label": _("Period Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
			currency_field(),
			currency_column(_("Basic"), "gh_pensionable_base", 120),
			currency_column(_("Allowances"), "gh_taxable_allowances", 120),
			currency_column(_("Gross Pay"), "gross_pay", 130),
			currency_column(_("SSNIT EE"), "gh_ssnit_employee", 115),
			currency_column(_("PF EE"), "gh_pf_employee", 115),
			currency_column(_("PAYE"), "gh_total_paye", 120),
			currency_column(_("Other Deductions"), "other_deductions", 150),
			currency_column(_("Total Deductions"), "total_deduction", 145),
			currency_column(_("Net Pay"), "net_pay", 130),
			currency_column(_("SSNIT ER"), "gh_ssnit_employer", 115),
			currency_column(_("PF ER"), "gh_pf_employer", 115),
			currency_column(_("Cost to Company"), "gh_employer_cost", 150),
			{"label": _("Salary Slip"), "fieldname": "salary_slip", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
		]
	)


def get_data(filters):
	rows = get_salary_slips(filters)
	for row in rows:
		statutory = (
			(row.get("gh_ssnit_employee") or 0)
			+ (row.get("gh_pf_employee") or 0)
			+ (row.get("gh_total_paye") or 0)
		)
		row["other_deductions"] = max((row.get("total_deduction") or 0) - statutory, 0)
	return rows


def get_chart(data):
	totals = {
		_("Net Pay"): sum(r.get("net_pay") or 0 for r in data),
		_("PAYE"): sum(r.get("gh_total_paye") or 0 for r in data),
		_("SSNIT"): sum((r.get("gh_ssnit_employee") or 0) + (r.get("gh_ssnit_employer") or 0) for r in data),
		_("Provident Fund"): sum((r.get("gh_pf_employee") or 0) + (r.get("gh_pf_employer") or 0) for r in data),
	}
	if not any(totals.values()):
		return None
	return {
		"data": {
			"labels": list(totals.keys()),
			"datasets": [{"name": _("Amount"), "values": list(totals.values())}],
		},
		"type": "donut",
	}


def get_summary(data):
	currency = data[0].get("currency") if data else None
	return [
		{"label": _("Slips"), "value": len(data), "indicator": "Blue", "datatype": "Int"},
		{"label": _("Gross Payroll"), "value": sum(r.get("gross_pay") or 0 for r in data), "datatype": "Currency", "options": currency},
		{"label": _("Net Payable"), "value": sum(r.get("net_pay") or 0 for r in data), "indicator": "Green", "datatype": "Currency", "options": currency},
		{"label": _("Statutory Remittance"), "value": sum((r.get("gh_total_paye") or 0) + (r.get("gh_ssnit_employee") or 0) + (r.get("gh_ssnit_employer") or 0) + (r.get("gh_pf_employee") or 0) + (r.get("gh_pf_employer") or 0) for r in data), "indicator": "Orange", "datatype": "Currency", "options": currency},
		{"label": _("Cost to Company"), "value": sum(r.get("gh_employer_cost") or 0 for r in data), "datatype": "Currency", "options": currency},
	]
