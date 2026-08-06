# Copyright (c) 2026, Ghana Payroll Contributors
# License: MIT

app_name = "ghana_payroll"
app_title = "Ghana Payroll"
app_publisher = "Ghana Payroll Contributors"
app_description = "Ghana localisation for ERPNext payroll: monthly graduated PAYE, SSNIT and Provident Fund"
app_email = "support@example.com"
app_license = "mit"
app_version = "1.0.5"

required_apps = ["frappe/erpnext", "frappe/hrms"]

# ---------------------------------------------------------------------------
# Replace the stock annualised PAYE engine with the Ghana monthly engine
# ---------------------------------------------------------------------------
override_doctype_class = {
	"Salary Slip": "ghana_payroll.overrides.salary_slip.GhanaSalarySlip",
	"Salary Structure Assignment": "ghana_payroll.overrides.salary_structure_assignment.GhanaSalaryStructureAssignment",
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
after_install = "ghana_payroll.install.after_install"
after_migrate = "ghana_payroll.install.after_migrate"
before_uninstall = "ghana_payroll.install.before_uninstall"

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
app_include_css = "/assets/ghana_payroll/css/ghana_payroll.css"

doctype_js = {
	"Salary Slip": "public/js/salary_slip.js",
}

# ---------------------------------------------------------------------------
# Fixtures (rates ship as data, not code)
# ---------------------------------------------------------------------------
fixtures = []
