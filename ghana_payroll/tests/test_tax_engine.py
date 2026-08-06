# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

"""
Run with:  bench --site <site> run-tests --app ghana_payroll
"""

import frappe

try:
	from frappe.tests import IntegrationTestCase as BaseTestCase
except ImportError:  # v15 and earlier
	from frappe.tests.utils import FrappeTestCase as BaseTestCase

from ghana_payroll.tax_engine import compute_paye, compute_payroll, get_settings


class TestGhanaTaxEngine(BaseTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		settings = frappe.get_doc("Ghana Payroll Settings")
		settings.ssnit_employee_rate = 5.5
		settings.ssnit_employer_rate = 13
		settings.pf_employee_rate = 10
		settings.pf_employer_rate = 5
		settings.apply_bonus_tax_rule = 0
		settings.limit_pension_relief = 0
		settings.flags.ignore_mandatory = True
		settings.save(ignore_permissions=True)
		frappe.db.commit()

	def test_tax_free_threshold(self):
		self.assertEqual(compute_paye(490)[0], 0.0)
		self.assertEqual(compute_paye(0)[0], 0.0)

	def test_band_boundaries(self):
		self.assertAlmostEqual(compute_paye(600)[0], 5.50, places=2)
		self.assertAlmostEqual(compute_paye(730)[0], 18.50, places=2)
		self.assertAlmostEqual(compute_paye(3896.67)[0], 572.67, places=2)
		self.assertAlmostEqual(compute_paye(19896.67)[0], 4572.67, places=2)
		self.assertAlmostEqual(compute_paye(50416.67)[0], 13728.67, places=2)

	def test_top_marginal_rate(self):
		base = compute_paye(50416.67)[0]
		self.assertAlmostEqual(compute_paye(60416.67)[0], base + 3500, places=2)

	def test_statutory_deductions(self):
		res = compute_payroll(basic=5000)
		self.assertAlmostEqual(res["ssnit_employee"], 275.00, places=2)
		self.assertAlmostEqual(res["ssnit_employer"], 650.00, places=2)
		self.assertAlmostEqual(res["pf_employee"], 500.00, places=2)
		self.assertAlmostEqual(res["pf_employer"], 250.00, places=2)

	def test_chargeable_income_formula(self):
		"""Gross - employee SSNIT - employee PF."""
		res = compute_payroll(basic=3000, taxable_allowances=1200)
		self.assertAlmostEqual(res["gross"], 4200.00, places=2)
		self.assertAlmostEqual(res["chargeable_income"], 4200 - 165 - 300, places=2)

	def test_exempt_and_relief(self):
		res = compute_payroll(basic=4000, taxable_allowances=500, exempt_allowances=300, relief=200)
		self.assertAlmostEqual(res["chargeable_income"], 3680.00, places=2)

	def test_bands_sum_to_total(self):
		total, breakdown = compute_paye(25000)
		self.assertAlmostEqual(sum(b["tax"] for b in breakdown), total, places=2)
		self.assertAlmostEqual(sum(b["chargeable"] for b in breakdown), 25000.00, places=2)

	def test_negative_chargeable_income_floors_at_zero(self):
		res = compute_payroll(basic=1000, relief=99999)
		self.assertEqual(res["chargeable_income"], 0.0)
		self.assertEqual(res["paye"], 0.0)

	def test_settings_are_loadable(self):
		settings = get_settings()
		self.assertTrue(settings.tax_brackets)
