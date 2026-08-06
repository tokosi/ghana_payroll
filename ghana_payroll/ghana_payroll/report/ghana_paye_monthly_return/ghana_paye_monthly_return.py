# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""
Ghana PAYE Monthly Return.

Mirrors the layout an employer needs when filing the monthly PAYE return with
the GRA: one row per employee showing gross emoluments, allowable deductions,
chargeable income and tax withheld.
"""

from frappe import _

from ghana_payroll.report_utils import (
	currency_column,
	currency_field,
	employee_columns,
	get_salary_slips,
)


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data, None, get_chart(data), get_summary(data)


def get_columns():
	return (
		employee_columns()
		+ [
			{"label": _("TIN"), "fieldname": "gh_tin", "fieldtype": "Data", "width": 130},
			{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
			{"label": _("Period Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
			currency_field(),
			currency_column(_("Basic"), "gh_pensionable_base"),
			currency_column(_("Allowances"), "gh_taxable_allowances"),
			currency_column(_("Gross Emoluments"), "gross_pay", 145),
			currency_column(_("SSNIT (5.5%)"), "gh_ssnit_employee"),
			currency_column(_("Provident Fund"), "gh_pf_employee"),
			currency_column(_("Exempt"), "gh_exempt_allowances", 110),
			currency_column(_("Reliefs"), "gh_tax_relief", 110),
			currency_column(_("Chargeable Income"), "gh_chargeable_income", 150),
			currency_column(_("PAYE"), "gh_paye"),
			currency_column(_("Bonus Tax"), "gh_bonus_tax", 110),
			currency_column(_("Total PAYE Payable"), "gh_total_paye", 155),
			{"label": _("Effective Rate"), "fieldname": "effective_rate", "fieldtype": "Percent", "width": 120},
			{"label": _("Salary Slip"), "fieldname": "salary_slip", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
		]
	)


def get_data(filters):
	rows = get_salary_slips(filters)
	for row in rows:
		gross = row.get("gross_pay") or 0
		row["effective_rate"] = round((row.get("gh_total_paye") or 0) / gross * 100, 2) if gross else 0
	return rows


def get_chart(data):
	top = sorted(data, key=lambda r: r.get("gh_total_paye") or 0, reverse=True)[:10]
	if not top:
		return None
	return {
		"data": {
			"labels": [r.get("employee_name") for r in top],
			"datasets": [{"name": _("PAYE"), "values": [r.get("gh_total_paye") or 0 for r in top]}],
		},
		"type": "bar",
		"colors": ["#c0392b"],
	}


def get_summary(data):
	total_paye = sum(r.get("gh_total_paye") or 0 for r in data)
	total_gross = sum(r.get("gross_pay") or 0 for r in data)
	currency = data[0].get("currency") if data else None
	return [
		{"label": _("Employees"), "value": len(data), "indicator": "Blue", "datatype": "Int"},
		{"label": _("Gross Emoluments"), "value": total_gross, "datatype": "Currency", "options": currency},
		{"label": _("Total PAYE Payable"), "value": total_paye, "indicator": "Red", "datatype": "Currency", "options": currency},
	]
