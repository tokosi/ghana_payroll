# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""Shared data access for the Ghana payroll reports."""

import frappe
from frappe import _


BASE_FIELDS = [
	"ss.name as salary_slip",
	"ss.employee",
	"ss.employee_name",
	"ss.department",
	"ss.designation",
	"ss.start_date",
	"ss.end_date",
	"ss.posting_date",
	"ss.currency",
	"ss.gross_pay",
	"ss.total_deduction",
	"ss.net_pay",
	"ss.gh_pensionable_base",
	"ss.gh_insurable_earnings",
	"ss.gh_taxable_allowances",
	"ss.gh_exempt_allowances",
	"ss.gh_bonus",
	"ss.gh_ssnit_employee",
	"ss.gh_ssnit_employer",
	"ss.gh_ssnit_tier1",
	"ss.gh_ssnit_tier2",
	"ss.gh_pf_employee",
	"ss.gh_pf_employer",
	"ss.gh_pension_relief",
	"ss.gh_tax_relief",
	"ss.gh_chargeable_income",
	"ss.gh_paye",
	"ss.gh_bonus_tax",
	"ss.gh_total_paye",
	"ss.gh_employer_cost",
	"emp.gh_tin",
	"emp.gh_ssnit_number",
	"emp.gh_tier2_scheme",
]


def validate_filters(filters):
	filters = frappe._dict(filters or {})
	if not filters.company:
		frappe.throw(_("Please select a Company."))
	if not filters.from_date or not filters.to_date:
		frappe.throw(_("Please select a date range."))
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date."))
	return filters


def get_salary_slips(filters):
	"""Fetch Ghana payroll figures for slips in the period."""
	filters = validate_filters(filters)

	conditions = ["ss.company = %(company)s", "ss.start_date >= %(from_date)s", "ss.end_date <= %(to_date)s"]

	if filters.get("docstatus") == "Draft and Submitted":
		conditions.append("ss.docstatus < 2")
	else:
		conditions.append("ss.docstatus = 1")

	if filters.get("department"):
		conditions.append("ss.department = %(department)s")
	if filters.get("employee"):
		conditions.append("ss.employee = %(employee)s")

	query = """
		SELECT {fields}
		FROM `tabSalary Slip` ss
		LEFT JOIN `tabEmployee` emp ON emp.name = ss.employee
		WHERE {conditions}
		ORDER BY ss.department, ss.employee_name, ss.start_date
	""".format(
		fields=", ".join(BASE_FIELDS), conditions=" AND ".join(conditions)
	)

	return frappe.db.sql(query, filters, as_dict=True)


def employee_columns(width=180):
	return [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": width},
	]


def currency_column(label, fieldname, width=130):
	return {
		"label": label,
		"fieldname": fieldname,
		"fieldtype": "Currency",
		"options": "currency",
		"width": width,
	}


def currency_field():
	return {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1, "width": 60}
