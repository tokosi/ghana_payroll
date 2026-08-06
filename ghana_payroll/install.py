# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""Idempotent setup for the Ghana Payroll app."""

import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

from ghana_payroll.tax_engine import DEFAULT_BRACKETS

PRINT_FORMAT_NAME = "Ghana Salary Slip"

SALARY_COMPONENTS = [
	{
		"salary_component": "Basic",
		"salary_component_abbr": "B",
		"type": "Earning",
		"is_tax_applicable": 1,
		"depends_on_payment_days": 1,
	},
	{
		"salary_component": "SSNIT Employee",
		"salary_component_abbr": "SSNITEE",
		"type": "Deduction",
		"depends_on_payment_days": 0,
		"description": "Tier 1 + Tier 2 employee contribution, 5.5% of basic. Calculated by Ghana Payroll.",
	},
	{
		"salary_component": "Provident Fund Employee",
		"salary_component_abbr": "PFEE",
		"type": "Deduction",
		"depends_on_payment_days": 0,
		"description": "Tier 3 employee contribution, 10% of basic. Calculated by Ghana Payroll.",
	},
	{
		"salary_component": "PAYE",
		"salary_component_abbr": "PAYE",
		"type": "Deduction",
		# HRMS renamed this flag. Set both; create_salary_components() skips
		# whichever one does not exist on the installed version.
		"variable_based_on_taxable_salary": 1,
		"is_income_tax_component": 1,
		"depends_on_payment_days": 0,
		"round_to_the_nearest_integer": 0,
		"description": "Ghana monthly graduated income tax. Calculated by Ghana Payroll.",
	},
	{
		"salary_component": "SSNIT Employer",
		"salary_component_abbr": "SSNITER",
		"type": "Deduction",
		"statistical_component": 1,
		"do_not_include_in_total": 1,
		"depends_on_payment_days": 0,
		"description": "Employer share, 13% of basic. Statistical: does not affect net pay.",
	},
	{
		"salary_component": "Provident Fund Employer",
		"salary_component_abbr": "PFER",
		"type": "Deduction",
		"statistical_component": 1,
		"do_not_include_in_total": 1,
		"depends_on_payment_days": 0,
		"description": "Employer Tier 3 share, 5% of basic. Statistical: does not affect net pay.",
	},
]


# ----------------------------------------------------------------------
# entry points
# ----------------------------------------------------------------------
def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	create_custom_fields_for_ghana()
	create_salary_components()
	seed_settings()
	ensure_tax_component_flag()
	create_income_tax_slabs()
	backfill_income_tax_slabs()
	create_print_format()
	create_workspace()
	frappe.db.commit()


# ----------------------------------------------------------------------
# custom fields
# ----------------------------------------------------------------------
def create_custom_fields_for_ghana():
	fields = {
		"Employee": [
			{
				"fieldname": "gh_ghana_section",
				"fieldtype": "Section Break",
				"label": "Ghana Statutory Details",
				"insert_after": "company",
				"collapsible": 1,
			},
			{
				"fieldname": "gh_tin",
				"fieldtype": "Data",
				"label": "TIN (Ghana Revenue Authority)",
				"insert_after": "gh_ghana_section",
			},
			{
				"fieldname": "gh_ssnit_number",
				"fieldtype": "Data",
				"label": "SSNIT Number",
				"insert_after": "gh_tin",
			},
			{"fieldname": "gh_ghana_cb", "fieldtype": "Column Break", "insert_after": "gh_ssnit_number"},
			{
				"fieldname": "gh_monthly_tax_relief",
				"fieldtype": "Currency",
				"label": "Monthly Tax Relief",
				"insert_after": "gh_ghana_cb",
				"description": "Approved personal reliefs (marriage/responsibility, child education, aged dependant, disability) expressed per month.",
			},
			{
				"fieldname": "gh_tier2_scheme",
				"fieldtype": "Data",
				"label": "Tier 2 Scheme / Trustee",
				"insert_after": "gh_monthly_tax_relief",
			},
		],
		"Salary Slip": [
			{
				"fieldname": "gh_section",
				"fieldtype": "Section Break",
				"label": "Ghana Payroll Computation",
				"insert_after": "total_in_words",
				"collapsible": 1,
			},
			{"fieldname": "gh_pensionable_base", "fieldtype": "Currency", "label": "Pensionable Basic", "insert_after": "gh_section", "read_only": 1},
			{"fieldname": "gh_insurable_earnings", "fieldtype": "Currency", "label": "Insurable Earnings", "insert_after": "gh_pensionable_base", "read_only": 1},
			{"fieldname": "gh_taxable_allowances", "fieldtype": "Currency", "label": "Taxable Allowances", "insert_after": "gh_insurable_earnings", "read_only": 1},
			{"fieldname": "gh_exempt_allowances", "fieldtype": "Currency", "label": "Tax Exempt Allowances", "insert_after": "gh_taxable_allowances", "read_only": 1},
			{"fieldname": "gh_bonus", "fieldtype": "Currency", "label": "Bonus", "insert_after": "gh_exempt_allowances", "read_only": 1},
			{"fieldname": "gh_cb1", "fieldtype": "Column Break", "insert_after": "gh_bonus"},
			{"fieldname": "gh_ssnit_employee", "fieldtype": "Currency", "label": "SSNIT (Employee)", "insert_after": "gh_cb1", "read_only": 1},
			{"fieldname": "gh_ssnit_employer", "fieldtype": "Currency", "label": "SSNIT (Employer)", "insert_after": "gh_ssnit_employee", "read_only": 1},
			{"fieldname": "gh_ssnit_tier1", "fieldtype": "Currency", "label": "SSNIT Tier 1", "insert_after": "gh_ssnit_employer", "read_only": 1},
			{"fieldname": "gh_ssnit_tier2", "fieldtype": "Currency", "label": "SSNIT Tier 2", "insert_after": "gh_ssnit_tier1", "read_only": 1},
			{"fieldname": "gh_pf_employee", "fieldtype": "Currency", "label": "Provident Fund (Employee)", "insert_after": "gh_ssnit_tier2", "read_only": 1},
			{"fieldname": "gh_pf_employer", "fieldtype": "Currency", "label": "Provident Fund (Employer)", "insert_after": "gh_pf_employee", "read_only": 1},
			{"fieldname": "gh_sec2", "fieldtype": "Section Break", "label": "Chargeable Income & PAYE", "insert_after": "gh_pf_employer"},
			{"fieldname": "gh_pension_relief", "fieldtype": "Currency", "label": "Pension Relief Allowed", "insert_after": "gh_sec2", "read_only": 1},
			{"fieldname": "gh_tax_relief", "fieldtype": "Currency", "label": "Personal Tax Relief", "insert_after": "gh_pension_relief", "read_only": 1},
			{"fieldname": "gh_chargeable_income", "fieldtype": "Currency", "label": "Chargeable Income", "insert_after": "gh_tax_relief", "read_only": 1, "bold": 1},
			{"fieldname": "gh_cb2", "fieldtype": "Column Break", "insert_after": "gh_chargeable_income"},
			{"fieldname": "gh_paye", "fieldtype": "Currency", "label": "PAYE (Graduated)", "insert_after": "gh_cb2", "read_only": 1},
			{"fieldname": "gh_bonus_tax", "fieldtype": "Currency", "label": "Bonus Tax", "insert_after": "gh_paye", "read_only": 1},
			{"fieldname": "gh_total_paye", "fieldtype": "Currency", "label": "Total PAYE", "insert_after": "gh_bonus_tax", "read_only": 1, "bold": 1},
			{"fieldname": "gh_employer_cost", "fieldtype": "Currency", "label": "Total Employer Cost", "insert_after": "gh_total_paye", "read_only": 1},
			{"fieldname": "gh_paye_breakdown", "fieldtype": "Long Text", "label": "PAYE Band Breakdown (JSON)", "insert_after": "gh_employer_cost", "read_only": 1, "hidden": 1, "print_hide": 1},
		],
	}
	create_custom_fields(fields, update=True)


# ----------------------------------------------------------------------
# salary components
# ----------------------------------------------------------------------
def create_salary_components():
	for spec in SALARY_COMPONENTS:
		name = spec["salary_component"]
		if frappe.db.exists("Salary Component", name):
			continue
		doc = frappe.new_doc("Salary Component")
		for key, value in spec.items():
			if doc.meta.has_field(key):
				doc.set(key, value)
		doc.flags.ignore_permissions = True
		try:
			doc.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(
				title="Ghana Payroll: could not create component {0}".format(name),
				message=frappe.get_traceback(),
			)


# ----------------------------------------------------------------------
# tax component flag
# ----------------------------------------------------------------------
TAX_FLAGS = ("is_income_tax_component", "variable_based_on_taxable_salary")


def get_tax_flag_fields():
	"""Whichever of the two flags this HRMS version actually has."""
	meta = frappe.get_meta("Salary Component")
	return [f for f in TAX_FLAGS if meta.has_field(f)]


@frappe.whitelist()
def ensure_tax_component_flag():
	"""
	Tick the income-tax flag on the mapped PAYE component.

	`add_tax_components()` only calls the tax hook for components carrying this
	flag, so without it the Ghana engine is never invoked and no PAYE row is
	produced. The fieldname differs across HRMS versions, hence the lookup.
	"""
	from ghana_payroll.tax_engine import get_settings

	try:
		component = get_settings().paye_component
	except Exception:
		component = None

	if not component or not frappe.db.exists("Salary Component", component):
		return None

	fields = get_tax_flag_fields()
	if not fields:
		return None

	changed = []
	doc = frappe.get_doc("Salary Component", component)
	for field in fields:
		if not cint(doc.get(field)):
			doc.set(field, 1)
			changed.append(field)

	if changed:
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)

	return {"component": component, "flags_set": changed, "available_flags": fields}


# ----------------------------------------------------------------------
# settings defaults
# ----------------------------------------------------------------------
def seed_settings():
	settings = frappe.get_doc("Ghana Payroll Settings")

	if not settings.tax_brackets:
		for band in DEFAULT_BRACKETS:
			settings.append("tax_brackets", band)

	if not settings.pensionable_components and frappe.db.exists("Salary Component", "Basic"):
		settings.append("pensionable_components", {"salary_component": "Basic", "note": "Basic salary"})

	defaults = {
		"currency": "GHS",
		"ssnit_employee_component": "SSNIT Employee",
		"ssnit_employer_component": "SSNIT Employer",
		"pf_employee_component": "Provident Fund Employee",
		"pf_employer_component": "Provident Fund Employer",
		"paye_component": "PAYE",
	}
	for field, value in defaults.items():
		if settings.get(field):
			continue
		if field != "currency" and not frappe.db.exists("Salary Component", value):
			continue
		settings.set(field, value)

	settings.flags.ignore_permissions = True
	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)


# ----------------------------------------------------------------------
# placeholder income tax slab
# ----------------------------------------------------------------------
SLAB_NAME = "Ghana PAYE - Managed by Ghana Payroll"


@frappe.whitelist()
def create_income_tax_slab(company=None):
	"""
	Create a submitted 0% Income Tax Slab.

	HRMS blocks a Salary Structure Assignment when the structure carries a
	component flagged `variable_based_on_taxable_salary` and no slab is linked.
	The Ghana engine takes its bands from Ghana Payroll Settings and never reads
	the slab, so an empty one satisfies the guard without changing any figure.
	"""
	if not company:
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		return None

	name = SLAB_NAME if not frappe.db.exists("Income Tax Slab", SLAB_NAME) else "{0} - {1}".format(SLAB_NAME, company)

	existing = frappe.db.get_value(
		"Income Tax Slab", {"company": company, "docstatus": 1, "name": ("like", SLAB_NAME + "%")}, "name"
	)
	if existing:
		return existing

	currency = frappe.db.get_value("Company", company, "default_currency") or "GHS"

	try:
		slab = frappe.new_doc("Income Tax Slab")
		slab.name = name
		slab.company = company
		slab.currency = currency
		slab.effective_from = "2020-01-01"
		slab.allow_tax_exemption = 0
		slab.append("slabs", {"from_amount": 0, "to_amount": 0, "percent_deduction": 0})
		slab.flags.ignore_permissions = True
		slab.insert(ignore_permissions=True)
		slab.submit()
		return slab.name
	except Exception:
		frappe.log_error(
			title="Ghana Payroll: could not create placeholder Income Tax Slab",
			message=frappe.get_traceback(),
		)
		return None


def create_income_tax_slabs():
	"""One placeholder slab per Ghanaian company."""
	companies = frappe.get_all("Company", filters={"country": "Ghana"}, pluck="name")
	for company in companies:
		create_income_tax_slab(company)


@frappe.whitelist()
def backfill_income_tax_slabs():
	"""
	Attach the placeholder slab to any assignment that is missing one.

	Only touches rows where the field is blank, and only while the Ghana engine
	is enabled. Existing links are never overwritten.
	"""
	from ghana_payroll.tax_engine import get_settings

	try:
		if not cint(get_settings().enabled):
			return 0
	except Exception:
		return 0

	updated = 0
	for company in frappe.get_all("Company", pluck="name"):
		names = frappe.get_all(
			"Salary Structure Assignment",
			filters={
				"company": company,
				"docstatus": ("<", 2),
				"income_tax_slab": ("in", ("", None)),
			},
			pluck="name",
		)
		if not names:
			continue

		slab = create_income_tax_slab(company)
		if not slab:
			continue

		for name in names:
			frappe.db.set_value(
				"Salary Structure Assignment", name, "income_tax_slab", slab, update_modified=False
			)
			updated += 1

	return updated


# ----------------------------------------------------------------------
# GL account mapping for salary components
# ----------------------------------------------------------------------
def _liability_parent(company):
	"""Best parent group for statutory payables."""
	for account_name in ("Duties and Taxes", "Current Liabilities", "Accounts Payable"):
		parent = frappe.db.get_value(
			"Account", {"company": company, "account_name": account_name, "is_group": 1}, "name"
		)
		if parent:
			return parent
	return frappe.db.get_value(
		"Account", {"company": company, "root_type": "Liability", "is_group": 1, "parent_account": ("is", "not set")}, "name"
	)


def _get_or_create_account(company, account_name, is_tax=False):
	existing = frappe.db.get_value("Account", {"company": company, "account_name": account_name}, "name")
	if existing:
		return existing

	parent = _liability_parent(company)
	if not parent:
		return None

	try:
		acc = frappe.new_doc("Account")
		acc.account_name = account_name
		acc.parent_account = parent
		acc.company = company
		acc.root_type = "Liability"
		acc.report_type = "Balance Sheet"
		acc.is_group = 0
		if is_tax:
			acc.account_type = "Tax"
		acc.flags.ignore_permissions = True
		acc.insert(ignore_permissions=True)
		return acc.name
	except Exception:
		frappe.log_error(
			title="Ghana Payroll: could not create account {0}".format(account_name),
			message=frappe.get_traceback(),
		)
		return None


def _set_component_account(component, company, account):
	"""Write the company/account row on a Salary Component."""
	if not component or not account:
		return False
	if not frappe.db.exists("Salary Component", component):
		return False

	doc = frappe.get_doc("Salary Component", component)

	child_doctype = doc.meta.get_field("accounts").options
	child_meta = frappe.get_meta(child_doctype)
	field = "account" if child_meta.has_field("account") else "default_account"

	row = None
	for r in doc.accounts or []:
		if r.company == company:
			row = r
			break
	if not row:
		row = doc.append("accounts", {"company": company})

	row.set(field, account)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def setup_component_accounts(company, ssnit_account=None, pf_account=None, paye_account=None):
	"""
	Point the mapped Ghana components at GL accounts.

	Reads the component names from Ghana Payroll Settings, so it works whatever
	you called them. Any account left blank is created under Duties and Taxes.
	"""
	from ghana_payroll.tax_engine import get_settings

	if not company:
		frappe.throw(frappe._("Company is required."))

	settings = get_settings()

	ssnit_account = ssnit_account or _get_or_create_account(company, "SSNIT Payable")
	pf_account = pf_account or _get_or_create_account(company, "Provident Fund Payable")
	paye_account = paye_account or _get_or_create_account(company, "PAYE Payable", is_tax=True)

	pairs = (
		(settings.ssnit_employee_component, ssnit_account),
		(settings.ssnit_employer_component, ssnit_account),
		(settings.pf_employee_component, pf_account),
		(settings.pf_employer_component, pf_account),
		(settings.paye_component, paye_account),
	)

	updated = []
	for component, account in pairs:
		if _set_component_account(component, company, account):
			updated.append("{0} -> {1}".format(component, account))

	frappe.db.commit()
	return updated


# ----------------------------------------------------------------------
# print format
# ----------------------------------------------------------------------
def create_print_format():
	path = os.path.join(
		frappe.get_app_path("ghana_payroll"), "templates", "print_formats", "ghana_salary_slip.html"
	)
	if not os.path.exists(path):
		return

	with open(path, "r", encoding="utf-8") as f:
		html = f.read()

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		doc = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
	else:
		doc = frappe.new_doc("Print Format")
		doc.name = PRINT_FORMAT_NAME

	doc.doc_type = "Salary Slip"
	doc.module = "Ghana Payroll"
	doc.standard = "No"
	doc.custom_format = 1
	doc.print_format_type = "Jinja"
	doc.disabled = 0
	doc.html = html
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)


# ----------------------------------------------------------------------
# workspace
# ----------------------------------------------------------------------
def create_workspace():
	"""Best effort: workspace schemas shift between versions, never block install."""
	try:
		if frappe.db.exists("Workspace", "Ghana Payroll"):
			return

		content = [
			{"id": "gh1", "type": "header", "data": {"text": "<span class='h4'>Ghana Payroll</span>", "col": 12}},
			{"id": "gh2", "type": "card", "data": {"card_name": "Configuration", "col": 4}},
			{"id": "gh3", "type": "card", "data": {"card_name": "Payroll Reports", "col": 4}},
		]

		ws = frappe.new_doc("Workspace")
		ws.name = "Ghana Payroll"
		ws.label = "Ghana Payroll"
		ws.title = "Ghana Payroll"
		ws.module = "Ghana Payroll"
		ws.public = 1
		ws.icon = "money-coins-1"
		ws.content = frappe.as_json(content)

		links = [
			("Card Break", "Configuration", None, None, 0),
			("Link", "Ghana Payroll Settings", "DocType", "Ghana Payroll Settings", 0),
			("Link", "Ghana PAYE Calculator", "Page", "ghana-paye-calculator", 0),
			("Link", "Salary Component", "DocType", "Salary Component", 0),
			("Link", "Salary Structure", "DocType", "Salary Structure", 0),
			("Card Break", "Payroll Reports", None, None, 0),
			("Link", "Ghana PAYE Monthly Return", "Report", "Ghana PAYE Monthly Return", 1),
			("Link", "Ghana SSNIT Contribution Schedule", "Report", "Ghana SSNIT Contribution Schedule", 1),
			("Link", "Ghana Provident Fund Schedule", "Report", "Ghana Provident Fund Schedule", 1),
			("Link", "Ghana Payroll Summary", "Report", "Ghana Payroll Summary", 1),
		]

		for link_type, label, kind, target, is_query in links:
			row = ws.append("links", {})
			row.type = link_type
			row.label = label
			row.hidden = 0
			row.onboard = 0
			if link_type == "Link":
				row.link_type = kind
				row.link_to = target
				if is_query:
					row.is_query_report = 1
					row.link_type = "Report"

		ws.flags.ignore_permissions = True
		ws.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title="Ghana Payroll: workspace creation skipped", message=frappe.get_traceback()
		)


def before_uninstall():
	"""Leave payroll data intact; only drop the print format and workspace."""
	for doctype, name in (("Print Format", PRINT_FORMAT_NAME), ("Workspace", "Ghana Payroll")):
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
