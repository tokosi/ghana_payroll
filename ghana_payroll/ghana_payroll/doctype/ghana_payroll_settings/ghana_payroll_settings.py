# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class GhanaPayrollSettings(Document):
	def validate(self):
		self.validate_brackets()
		self.validate_components()
		self.validate_rates()

	def validate_brackets(self):
		if not self.tax_brackets:
			frappe.throw(_("At least one PAYE tax bracket is required."))

		finals = [b for b in self.tax_brackets if cint(b.is_final)]
		if len(finals) > 1:
			frappe.throw(_("Only one bracket can be marked as the final 'Exceeding' band."))
		if not finals:
			frappe.msgprint(
				_("No final band is marked. Income above the last band will not be taxed."),
				indicator="orange",
				title=_("Check PAYE Bands"),
			)
		elif finals[0].idx != len(self.tax_brackets):
			frappe.throw(_("The final 'Exceeding' band must be the last row."))

		for b in self.tax_brackets:
			if not cint(b.is_final) and flt(b.chargeable_income) <= 0:
				frappe.throw(
					_("Row {0}: Chargeable Income must be greater than zero for non-final bands.").format(b.idx)
				)
			if flt(b.rate) < 0 or flt(b.rate) > 100:
				frappe.throw(_("Row {0}: Rate must be between 0 and 100.").format(b.idx))

	def validate_components(self):
		if not self.pensionable_components:
			frappe.throw(
				_("Add at least one Pensionable Component (normally 'Basic'). SSNIT and Provident Fund are calculated on it.")
			)

		if self.paye_component:
			variable = frappe.db.get_value(
				"Salary Component", self.paye_component, "variable_based_on_taxable_salary"
			)
			if not cint(variable):
				frappe.msgprint(
					_("Salary Component {0} does not have 'Variable Based On Taxable Salary' ticked. PAYE will not be calculated automatically.").format(
						frappe.bold(self.paye_component)
					),
					indicator="red",
					title=_("PAYE Component Misconfigured"),
				)

		for field in ("ssnit_employer_component", "pf_employer_component"):
			component = self.get(field)
			if not component:
				continue
			if not cint(frappe.db.get_value("Salary Component", component, "statistical_component")):
				frappe.msgprint(
					_("Employer contribution {0} is not a statistical component, so it will reduce employee net pay.").format(
						frappe.bold(component)
					),
					indicator="orange",
				)

	def validate_rates(self):
		total = flt(self.ssnit_tier1_rate) + flt(self.ssnit_tier2_rate)
		combined = flt(self.ssnit_employee_rate) + flt(self.ssnit_employer_rate)
		if total and abs(total - combined) > 0.01:
			frappe.msgprint(
				_("Tier 1 + Tier 2 ({0}%) does not equal Employee + Employer SSNIT ({1}%).").format(total, combined),
				indicator="orange",
			)

	def on_update(self):
		frappe.clear_cache(doctype="Ghana Payroll Settings")


@frappe.whitelist()
def reset_default_brackets():
	"""Restore the statutory GRA monthly bands."""
	from ghana_payroll.tax_engine import DEFAULT_BRACKETS

	doc = frappe.get_doc("Ghana Payroll Settings")
	doc.tax_brackets = []
	for b in DEFAULT_BRACKETS:
		doc.append("tax_brackets", b)
	doc.save()
	return len(DEFAULT_BRACKETS)
