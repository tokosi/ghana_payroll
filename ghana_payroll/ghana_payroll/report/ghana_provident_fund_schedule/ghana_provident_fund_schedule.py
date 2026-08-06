# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""Ghana Provident Fund (Tier 3) Schedule: employee 10% + employer 5% of basic."""

from frappe import _

from ghana_payroll.report_utils import (
	currency_column,
	currency_field,
	employee_columns,
	get_salary_slips,
)


def execute(filters=None):
	data = get_data(filters)
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return (
		employee_columns()
		+ [
			{"label": _("SSNIT Number"), "fieldname": "gh_ssnit_number", "fieldtype": "Data", "width": 140},
			{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
			{"label": _("Period Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
			currency_field(),
			currency_column(_("Basic Salary"), "gh_pensionable_base", 140),
			currency_column(_("Employee (10%)"), "gh_pf_employee", 145),
			currency_column(_("Employer (5%)"), "gh_pf_employer", 140),
			currency_column(_("Total Contribution"), "total_contribution", 155),
			{"label": _("Salary Slip"), "fieldname": "salary_slip", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
		]
	)


def get_data(filters):
	rows = get_salary_slips(filters)
	for row in rows:
		row["total_contribution"] = (row.get("gh_pf_employee") or 0) + (row.get("gh_pf_employer") or 0)
	return [r for r in rows if r["total_contribution"]]


def get_summary(data):
	currency = data[0].get("currency") if data else None
	return [
		{"label": _("Members"), "value": len(data), "indicator": "Blue", "datatype": "Int"},
		{
			"label": _("Employee Contributions"),
			"value": sum(r.get("gh_pf_employee") or 0 for r in data),
			"datatype": "Currency",
			"options": currency,
		},
		{
			"label": _("Employer Contributions"),
			"value": sum(r.get("gh_pf_employer") or 0 for r in data),
			"datatype": "Currency",
			"options": currency,
		},
		{
			"label": _("Total Remittance"),
			"value": sum(r.get("total_contribution") or 0 for r in data),
			"indicator": "Green",
			"datatype": "Currency",
			"options": currency,
		},
	]
