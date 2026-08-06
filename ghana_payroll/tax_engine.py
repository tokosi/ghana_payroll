# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""
Ghana PAYE / statutory computation engine.

This module is the single source of truth for every Ghana payroll figure.
Both the Salary Slip override and the standalone PAYE Calculator page call
`compute_payroll()`, so a slip and the calculator can never disagree.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

SETTINGS = "Ghana Payroll Settings"

# Monthly graduated bands (Act 896 as amended by Act 1111).
# Annual equivalents: 5,880 / 1,320 / 1,560 / 38,000 / 192,000 / 366,240 / above.
DEFAULT_BRACKETS = [
	{"band_name": "First", "chargeable_income": 490.00, "rate": 0.0, "is_final": 0},
	{"band_name": "Next", "chargeable_income": 110.00, "rate": 5.0, "is_final": 0},
	{"band_name": "Next", "chargeable_income": 130.00, "rate": 10.0, "is_final": 0},
	{"band_name": "Next", "chargeable_income": 3166.67, "rate": 17.5, "is_final": 0},
	{"band_name": "Next", "chargeable_income": 16000.00, "rate": 25.0, "is_final": 0},
	{"band_name": "Next", "chargeable_income": 30520.00, "rate": 30.0, "is_final": 0},
	{"band_name": "Exceeding", "chargeable_income": 0.00, "rate": 35.0, "is_final": 1},
]


def get_settings():
	"""Cached Ghana Payroll Settings single doc."""
	return frappe.get_cached_doc(SETTINGS)


def get_brackets(settings=None):
	"""Return the configured bands, falling back to statutory defaults."""
	settings = settings or get_settings()
	rows = [
		{
			"band_name": b.band_name,
			"chargeable_income": flt(b.chargeable_income),
			"rate": flt(b.rate),
			"is_final": cint(b.is_final),
		}
		for b in (settings.get("tax_brackets") or [])
	]
	return rows or [dict(b) for b in DEFAULT_BRACKETS]


def compute_paye(chargeable_income, settings=None, brackets=None):
	"""
	Walk the monthly graduated bands and return (tax, breakdown).

	Ghana taxes each slice of income at its own rate, so the tax is the sum of
	band_width * band_rate for every band the income reaches into. The final
	band ("Exceeding") absorbs whatever is left over.
	"""
	settings = settings or get_settings()
	brackets = brackets or get_brackets(settings)

	remaining = flt(chargeable_income)
	total_tax = 0.0
	cumulative_from = 0.0
	breakdown = []

	if remaining <= 0:
		return 0.0, breakdown

	for band in brackets:
		if remaining <= 0:
			break

		width = flt(band.get("chargeable_income"))
		if cint(band.get("is_final")) or width <= 0:
			taxed = remaining
		else:
			taxed = min(remaining, width)

		rate = flt(band.get("rate"))
		tax = flt(taxed * rate / 100.0, 2)
		total_tax += tax

		breakdown.append(
			{
				"band": band.get("band_name") or "Next",
				"from_amount": flt(cumulative_from, 2),
				"to_amount": flt(cumulative_from + taxed, 2),
				"chargeable": flt(taxed, 2),
				"rate": rate,
				"tax": tax,
			}
		)

		cumulative_from += taxed
		remaining -= taxed

	return flt(total_tax, 2), breakdown


def _capped(amount, base, cap_percent):
	"""Apply a percentage-of-base ceiling; cap_percent of 0 means no ceiling."""
	if not cap_percent:
		return flt(amount)
	return min(flt(amount), flt(base) * flt(cap_percent) / 100.0)


def compute_payroll(
	basic=0.0,
	taxable_allowances=0.0,
	exempt_allowances=0.0,
	bonus=0.0,
	relief=0.0,
	settings=None,
):
	"""
	Full monthly Ghana computation.

	Chargeable income = Gross Pay
	                    - Employee SSNIT (% of pensionable basic)
	                    - Employee Provident Fund (% of pensionable basic)
	                    - Tax exempt allowances
	                    - Personal reliefs
	                    (- concessionary bonus, when the bonus rule is on)
	"""
	settings = settings or get_settings()

	basic = flt(basic)
	taxable_allowances = flt(taxable_allowances)
	exempt_allowances = flt(exempt_allowances)
	bonus = flt(bonus)
	relief = flt(relief)

	gross = flt(basic + taxable_allowances + exempt_allowances + bonus, 2)

	# --- Insurable earnings ceiling / floor (SSNIT publishes these annually) ---
	insurable = basic
	if flt(settings.ssnit_max_insurable_earnings):
		insurable = min(insurable, flt(settings.ssnit_max_insurable_earnings))
	if flt(settings.ssnit_min_insurable_earnings) and insurable:
		insurable = max(insurable, flt(settings.ssnit_min_insurable_earnings))

	# --- Tier 1 + Tier 2 (SSNIT) ---
	ssnit_employee = flt(insurable * flt(settings.ssnit_employee_rate) / 100.0, 2)
	ssnit_employer = flt(insurable * flt(settings.ssnit_employer_rate) / 100.0, 2)
	ssnit_tier1 = flt(insurable * flt(settings.ssnit_tier1_rate) / 100.0, 2)
	ssnit_tier2 = flt(insurable * flt(settings.ssnit_tier2_rate) / 100.0, 2)

	# --- Tier 3 (Provident Fund) ---
	pf_employee = flt(basic * flt(settings.pf_employee_rate) / 100.0, 2)
	pf_employer = flt(basic * flt(settings.pf_employer_rate) / 100.0, 2)

	# --- Relief actually allowed against chargeable income ---
	pension_relief = ssnit_employee + pf_employee
	if cint(settings.limit_pension_relief):
		pension_relief = _capped(pension_relief, basic, flt(settings.pension_relief_cap_percent))
	pension_relief = flt(pension_relief, 2)

	# --- Concessionary bonus treatment (optional) ---
	bonus_tax = 0.0
	concessionary_bonus = 0.0
	if cint(settings.apply_bonus_tax_rule) and bonus:
		threshold = flt(basic) * 12.0 * flt(settings.bonus_threshold_percent) / 100.0
		concessionary_bonus = min(bonus, threshold)
		bonus_tax = flt(concessionary_bonus * flt(settings.bonus_tax_rate) / 100.0, 2)

	chargeable_income = flt(
		gross - exempt_allowances - pension_relief - relief - concessionary_bonus, 2
	)
	if chargeable_income < 0:
		chargeable_income = 0.0

	paye, breakdown = compute_paye(chargeable_income, settings=settings)

	if cint(settings.round_paye):
		paye = flt(paye, 2)

	total_paye = flt(paye + bonus_tax, 2)
	statutory_deductions = flt(ssnit_employee + pf_employee + total_paye, 2)

	return {
		"basic": flt(basic, 2),
		"insurable_earnings": flt(insurable, 2),
		"taxable_allowances": flt(taxable_allowances, 2),
		"exempt_allowances": flt(exempt_allowances, 2),
		"bonus": flt(bonus, 2),
		"gross": gross,
		"ssnit_employee": ssnit_employee,
		"ssnit_employer": ssnit_employer,
		"ssnit_tier1": ssnit_tier1,
		"ssnit_tier2": ssnit_tier2,
		"pf_employee": pf_employee,
		"pf_employer": pf_employer,
		"pension_relief": pension_relief,
		"personal_relief": flt(relief, 2),
		"concessionary_bonus": flt(concessionary_bonus, 2),
		"bonus_tax": bonus_tax,
		"chargeable_income": chargeable_income,
		"paye": paye,
		"total_paye": total_paye,
		"statutory_deductions": statutory_deductions,
		"net_pay": flt(gross - statutory_deductions, 2),
		"employer_cost": flt(gross + ssnit_employer + pf_employer, 2),
		"breakdown": breakdown,
	}


@frappe.whitelist()
def calculate(
	basic=0,
	taxable_allowances=0,
	exempt_allowances=0,
	bonus=0,
	relief=0,
):
	"""Whitelisted entry point for the Ghana PAYE Calculator page."""
	result = compute_payroll(
		basic=flt(basic),
		taxable_allowances=flt(taxable_allowances),
		exempt_allowances=flt(exempt_allowances),
		bonus=flt(bonus),
		relief=flt(relief),
	)
	settings = get_settings()
	result["currency"] = settings.currency or "GHS"
	result["enabled"] = cint(settings.enabled)
	return result


@frappe.whitelist()
def get_effective_rate(basic=0, taxable_allowances=0):
	"""Convenience helper: effective PAYE rate on gross."""
	res = compute_payroll(basic=flt(basic), taxable_allowances=flt(taxable_allowances))
	gross = res["gross"] or 1
	return {
		"effective_rate": flt(res["total_paye"] / gross * 100.0, 2),
		"marginal_rate": res["breakdown"][-1]["rate"] if res["breakdown"] else 0.0,
	}
