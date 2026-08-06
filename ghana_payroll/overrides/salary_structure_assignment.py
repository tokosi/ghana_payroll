# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""
Relax the Income Tax Slab requirement on Salary Structure Assignment.

HRMS refuses to save an assignment when the Salary Structure contains a
component flagged `variable_based_on_taxable_salary` (our PAYE component) and no
Income Tax Slab is linked. That guard exists because the stock engine reads its
rates from the slab.

The Ghana engine reads its bands from Ghana Payroll Settings and never touches
the slab, so the requirement is noise. When the engine is enabled we skip it. If
a slab *is* linked we still run the stock validation, which checks the currency
matches, and if the engine is disabled we defer to stock behaviour entirely.
"""

import frappe
from frappe.utils import cint

from ghana_payroll.tax_engine import get_settings

try:
	from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
		SalaryStructureAssignment,
	)
except ImportError:  # pragma: no cover - legacy layout
	from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
		SalaryStructureAssignment,
	)


def _ghana_enabled():
	try:
		return bool(cint(get_settings().enabled))
	except Exception:
		return False


class GhanaSalaryStructureAssignment(SalaryStructureAssignment):
	def validate_income_tax_slab(self, *args, **kwargs):
		# Nothing linked and the Ghana engine is live: the slab is irrelevant.
		if _ghana_enabled() and not self.income_tax_slab:
			return
		parent = getattr(super(), "validate_income_tax_slab", None)
		if parent:
			return parent(*args, **kwargs)

	def warn_about_missing_income_tax_slab(self, *args, **kwargs):
		if _ghana_enabled() and not self.income_tax_slab:
			return
		parent = getattr(super(), "warn_about_missing_income_tax_slab", None)
		if parent:
			return parent(*args, **kwargs)
