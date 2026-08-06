# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""
Overrides the HRMS/ERPNext Salary Slip so PAYE follows Ghana's *monthly*
graduated bands instead of the stock annualised projection.

Design notes
------------
* We hook `calculate_variable_based_on_taxable_salary()`, which is the single
  point where the stock engine produces a tax figure. Returning our own number
  there means the rest of the slip lifecycle (totals, rounding, payment days,
  loan repayment, submission) is untouched.
* SSNIT and Provident Fund amounts are computed from the pensionable base
  rather than read off the deduction rows. Salary Structure row order is not
  guaranteed, so deriving them ourselves makes PAYE independent of whether the
  SSNIT row happens to be calculated before or after the PAYE row.
* Statutory deduction rows are then written back after the stock deduction
  pass, before totals are struck.
"""

import json

import frappe
from frappe.utils import cint, escape_html, flt, fmt_money

from ghana_payroll.tax_engine import compute_payroll, get_settings

try:  # v14+ payroll lives in the HRMS app
	from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
except ImportError:  # pragma: no cover - legacy layout
	from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip


class GhanaSalarySlip(SalarySlip):
	# ------------------------------------------------------------------
	# helpers
	# ------------------------------------------------------------------
	def gh_enabled(self):
		try:
			return bool(cint(get_settings().enabled))
		except Exception:
			return False

	def gh_row_amount(self, row):
		"""
		Amount for a component row after payment-day proration.

		The signature of `get_amount_based_on_payment_days` has changed between
		versions, so try the known shapes and fall back to the raw amount.
		"""
		fn = getattr(self, "get_amount_based_on_payment_days", None)
		if fn:
			attempts = (
				(row,),
				(row, getattr(self, "joining_date", None), getattr(self, "relieving_date", None)),
			)
			for args in attempts:
				try:
					res = fn(*args)
				except TypeError:
					continue
				except Exception:
					break
				if isinstance(res, (list, tuple)):
					return flt(res[0])
				return flt(res)
		return flt(row.amount)

	def gh_sum(self, table, component_names):
		names = set(component_names or [])
		if not names:
			return 0.0
		return flt(
			sum(
				self.gh_row_amount(r)
				for r in (self.get(table) or [])
				if r.salary_component in names
			)
		)

	def gh_personal_relief(self):
		settings = get_settings()
		if not cint(settings.apply_employee_tax_relief) or not self.employee:
			return 0.0
		return flt(
			frappe.db.get_value("Employee", self.employee, "gh_monthly_tax_relief") or 0
		)

	# ------------------------------------------------------------------
	# computation
	# ------------------------------------------------------------------
	def gh_compute(self, force=False):
		"""Compute (and memoise) the Ghana figures for this slip."""
		if not force and getattr(self, "_gh_result", None):
			return self._gh_result

		settings = get_settings()

		pensionable = [d.salary_component for d in (settings.pensionable_components or [])]
		exempt = [d.salary_component for d in (settings.tax_exempt_components or [])]
		bonus_components = (
			[d.salary_component for d in (settings.bonus_components or [])]
			if cint(settings.apply_bonus_tax_rule)
			else []
		)

		basic = self.gh_sum("earnings", pensionable)
		exempt_amount = self.gh_sum("earnings", exempt)
		bonus = self.gh_sum("earnings", bonus_components)

		gross = flt(self.gross_pay)
		if not gross:
			try:
				gross = flt(self.get_component_totals("earnings", depends_on_payment_days=1))
			except Exception:
				gross = flt(sum(self.gh_row_amount(r) for r in (self.earnings or [])))

		taxable_allowances = flt(gross - basic - exempt_amount - bonus)
		if taxable_allowances < 0:
			taxable_allowances = 0.0

		self._gh_result = compute_payroll(
			basic=basic,
			taxable_allowances=taxable_allowances,
			exempt_allowances=exempt_amount,
			bonus=bonus,
			relief=self.gh_personal_relief(),
			settings=settings,
		)
		return self._gh_result

	# ------------------------------------------------------------------
	# overridden hooks
	# ------------------------------------------------------------------
	def calculate_variable_based_on_taxable_salary(self, *args, **kwargs):
		"""Replace the annualised ERPNext tax engine with Ghana monthly PAYE."""
		if not self.gh_enabled():
			return super().calculate_variable_based_on_taxable_salary(*args, **kwargs)
		return flt(self.gh_compute(force=True)["total_paye"], 2)

	def calculate_variable_tax(self, *args, **kwargs):
		"""
		Fallback hook.

		Older HRMS routes through `calculate_variable_based_on_taxable_salary`,
		which then calls this. If a version calls this one directly, we still
		want the Ghana figure rather than the annualised projection.
		"""
		if not self.gh_enabled():
			return super().calculate_variable_tax(*args, **kwargs)
		return flt(self.gh_compute(force=True)["total_paye"], 2)

	def calculate_component_amounts(self, component_type, *args, **kwargs):
		super().calculate_component_amounts(component_type, *args, **kwargs)
		if component_type == "deductions" and self.gh_enabled():
			self.gh_apply_statutory_rows()

	def compute_income_tax_breakup(self, *args, **kwargs):
		"""The annual tax-breakup panel is meaningless under monthly PAYE."""
		if self.gh_enabled():
			return
		parent = getattr(super(), "compute_income_tax_breakup", None)
		if parent:
			return parent(*args, **kwargs)

	# ------------------------------------------------------------------
	# writing results back onto the slip
	# ------------------------------------------------------------------
	def gh_set_component_amount(self, component, amount, table="deductions"):
		"""Set (or create) a salary detail row and pin its amount."""
		if not component:
			return

		row = None
		for d in self.get(table) or []:
			if d.salary_component == component:
				row = d
				break

		if not row:
			if not flt(amount):
				return
			meta = frappe.db.get_value(
				"Salary Component",
				component,
				["salary_component_abbr", "statistical_component", "do_not_include_in_total"],
				as_dict=True,
			)
			if not meta:
				return
			row = self.append(table, {})
			row.salary_component = component
			row.abbr = meta.salary_component_abbr
			row.statistical_component = cint(meta.statistical_component)
			row.do_not_include_in_total = cint(meta.do_not_include_in_total)

		row.amount = flt(amount, 2)
		row.default_amount = flt(amount, 2)
		row.additional_amount = 0
		row.amount_based_on_formula = 0
		row.depends_on_payment_days = 0
		row.condition = None
		row.formula = None

	def gh_apply_statutory_rows(self):
		settings = get_settings()
		res = self.gh_compute(force=True)

		# PAYE is written directly rather than left to HRMS `add_tax_components()`.
		# That path only fires when the component carries the income-tax flag, sits
		# on the structure with a blank amount and formula, and a Payroll Period
		# covers the dates. Any one of those missing and it skips silently, leaving
		# the slip with no tax row at all. Writing it here removes the dependency.
		self.gh_set_component_amount(settings.paye_component, res["total_paye"])

		self.gh_set_component_amount(settings.ssnit_employee_component, res["ssnit_employee"])
		self.gh_set_component_amount(settings.pf_employee_component, res["pf_employee"])
		self.gh_set_component_amount(settings.ssnit_employer_component, res["ssnit_employer"])
		self.gh_set_component_amount(settings.pf_employer_component, res["pf_employer"])

		self.gh_store_summary(res)

	def gh_render_breakdown(self, res):
		"""
		Pre-render the band table for the payslip.

		The print sandbox has no JSON parser, and calling a method from the
		template couples the payslip to whatever code the worker happens to
		have loaded. Storing finished markup means a stale or older process
		yields a payslip missing this panel rather than a print error.
		"""
		rows = (res or {}).get("breakdown") or []
		if not rows:
			return ""

		currency = self.currency or "GHS"

		def money(value):
			try:
				return fmt_money(flt(value), currency=currency)
			except Exception:
				return "{:,.2f}".format(flt(value))

		body = []
		for band in rows:
			body.append(
				"<tr><td>{band} {chargeable}</td><td class='amt'>{chargeable}</td>"
				"<td class='amt'>{rate}%</td><td class='amt'>{tax}</td></tr>".format(
					band=escape_html(str(band.get("band") or "")),
					chargeable=money(band.get("chargeable")),
					rate=flt(band.get("rate")),
					tax=money(band.get("tax")),
				)
			)

		return (
			"<table class='gh-tbl'><thead><tr><th>PAYE Band</th>"
			"<th class='amt'>Chargeable ({cur})</th><th class='amt'>Rate</th>"
			"<th class='amt'>Tax ({cur})</th></tr></thead><tbody>{body}</tbody>"
			"<tfoot><tr class='tot'><td colspan='3'>Total PAYE</td>"
			"<td class='amt'>{total}</td></tr></tfoot></table>"
		).format(cur=currency, body="".join(body), total=money((res or {}).get("total_paye")))

	def gh_breakdown_rows(self):
		"""
		Band breakdown for the print format.

		The Jinja print sandbox does not expose a JSON parser, so the decoding
		happens here. Never raises: a broken payload yields an empty table
		rather than a failed payslip.
		"""
		try:
			rows = json.loads(self.get("gh_paye_breakdown") or "[]")
			return rows if isinstance(rows, list) else []
		except Exception:
			return []

	def gh_store_summary(self, res=None):
		res = res or self.gh_compute()
		self.gh_pensionable_base = res["basic"]
		self.gh_insurable_earnings = res["insurable_earnings"]
		self.gh_taxable_allowances = res["taxable_allowances"]
		self.gh_exempt_allowances = res["exempt_allowances"]
		self.gh_bonus = res["bonus"]
		self.gh_ssnit_employee = res["ssnit_employee"]
		self.gh_ssnit_employer = res["ssnit_employer"]
		self.gh_ssnit_tier1 = res["ssnit_tier1"]
		self.gh_ssnit_tier2 = res["ssnit_tier2"]
		self.gh_pf_employee = res["pf_employee"]
		self.gh_pf_employer = res["pf_employer"]
		self.gh_pension_relief = res["pension_relief"]
		self.gh_tax_relief = res["personal_relief"]
		self.gh_chargeable_income = res["chargeable_income"]
		self.gh_paye = res["paye"]
		self.gh_bonus_tax = res["bonus_tax"]
		self.gh_total_paye = res["total_paye"]
		self.gh_employer_cost = res["employer_cost"]
		try:
			self.gh_paye_breakdown = json.dumps(res["breakdown"])
		except Exception:
			self.gh_paye_breakdown = "[]"

		try:
			self.gh_paye_breakdown_html = self.gh_render_breakdown(res)
		except Exception:
			self.gh_paye_breakdown_html = ""

	def validate(self):
		super().validate()
		if self.gh_enabled():
			self.gh_store_summary()
