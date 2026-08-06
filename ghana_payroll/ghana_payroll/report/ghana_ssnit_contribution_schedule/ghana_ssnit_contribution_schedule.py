# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""
Ghana SSNIT Contribution Schedule.

Splits the 18.5% total contribution into Tier 1 (13.5%, remitted to SSNIT) and
Tier 2 (5%, remitted to the approved corporate trustee), which is how the
monthly contribution report has to be filed.
"""

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
			{"label": _("Tier 2 Scheme"), "fieldname": "gh_tier2_scheme", "fieldtype": "Data", "width": 150},
			{"label": _("Period Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
			currency_field(),
			currency_column(_("Basic Salary"), "gh_pensionable_base", 140),
			currency_column(_("Insurable Earnings"), "gh_insurable_earnings", 150),
			currency_column(_("Employee (5.5%)"), "gh_ssnit_employee", 145),
			currency_column(_("Employer (13%)"), "gh_ssnit_employer", 140),
			currency_column(_("Total (18.5%)"), "total_contribution", 140),
			currency_column(_("Tier 1 (13.5%)"), "gh_ssnit_tier1", 140),
			currency_column(_("Tier 2 (5%)"), "gh_ssnit_tier2", 130),
			{"label": _("Salary Slip"), "fieldname": "salary_slip", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
		]
	)


def get_data(filters):
	rows = get_salary_slips(filters)
	for row in rows:
		row["total_contribution"] = (row.get("gh_ssnit_employee") or 0) + (row.get("gh_ssnit_employer") or 0)
	return rows


def get_summary(data):
	currency = data[0].get("currency") if data else None
	return [
		{"label": _("Contributors"), "value": len(data), "indicator": "Blue", "datatype": "Int"},
		{
			"label": _("Tier 1 Remittance"),
			"value": sum(r.get("gh_ssnit_tier1") or 0 for r in data),
			"datatype": "Currency",
			"options": currency,
		},
		{
			"label": _("Tier 2 Remittance"),
			"value": sum(r.get("gh_ssnit_tier2") or 0 for r in data),
			"datatype": "Currency",
			"options": currency,
		},
		{
			"label": _("Total Contribution"),
			"value": sum(r.get("total_contribution") or 0 for r in data),
			"indicator": "Green",
			"datatype": "Currency",
			"options": currency,
		},
	]
