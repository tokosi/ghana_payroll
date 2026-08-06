# Ghana Payroll for ERPNext v16

A Frappe/ERPNext app that replaces the stock annualised PAYE engine with Ghana's
**monthly graduated** tax rules, and adds SSNIT, Provident Fund, a Ghana payslip
layout, statutory reports and configuration screens.

---

## What it does

| Feature | Detail |
|---|---|
| PAYE | Monthly progressive bands, applied slice by slice |
| Chargeable income | `Gross Pay − Employee SSNIT − Employee Provident Fund` (plus exempt allowances and reliefs) |
| Employee SSNIT | 5.5% of pensionable basic — deducted |
| Employer SSNIT | 13% of pensionable basic — statistical, does not touch net pay |
| Employee Provident Fund | 10% of basic — deducted |
| Employer Provident Fund | 5% of basic — statistical |
| Tier split | Tier 1 (13.5%) / Tier 2 (5%) shown separately for filing |
| Insurable earnings ceiling | Configurable cap on the SSNIT base (default GHS 69,000/month) |
| Reliefs | Per-employee monthly personal relief field |
| Bonus concession | Optional flat rate on bonus up to a % of annual basic |
| Calculator | Standalone PAYE calculator page |
| Payslip | Ghana-format print layout with the full PAYE working |
| Reports | PAYE Monthly Return, SSNIT Schedule, Provident Fund Schedule, Payroll Summary |

### Default monthly bands (GRA graduated schedule)

| Band | Chargeable income (GHS) | Rate |
|---|---|---|
| First | 490.00 | 0% |
| Next | 110.00 | 5% |
| Next | 130.00 | 10% |
| Next | 3,166.67 | 17.5% |
| Next | 16,000.00 | 25% |
| Next | 30,520.00 | 30% |
| Exceeding | 50,416.67 | 35% |

Bands are **data, not code** — edit them in Ghana Payroll Settings whenever the
GRA revises the schedule. Verify against the current GRA publication before each
tax year; nothing in this app files anything on your behalf.

---

## Installation

Prerequisites: a working bench with `erpnext` and `hrms` installed.

### Option A — the installer script

```bash
cd ~/frappe-bench
./path/to/ghana_payroll/install.sh yoursite.local
```

### Option B — bench commands

```bash
# 1. change into your bench
cd ~/frappe-bench

# 2. add the app to the bench (from a local folder)
bench get-app ghana_payroll /path/to/ghana_payroll

#    ...or from a git remote
#    bench get-app https://github.com/youruser/ghana_payroll.git

# 3. install onto your site
bench --site yoursite.local install-app ghana_payroll

# 4. sync schema and run setup
bench --site yoursite.local migrate

# 5. build the JS/CSS bundles
bench build --app ghana_payroll

# 6. clear cache and restart
bench --site yoursite.local clear-cache
bench restart
```

### If `erpnext` / `hrms` are missing

```bash
bench get-app erpnext
bench get-app hrms
bench --site yoursite.local install-app erpnext
bench --site yoursite.local install-app hrms
```

### Verify

```bash
bench --site yoursite.local run-tests --app ghana_payroll
bench --site yoursite.local console
>>> from ghana_payroll.tax_engine import compute_payroll
>>> compute_payroll(basic=5000)["paye"]
```

### Update

```bash
cd ~/frappe-bench/apps/ghana_payroll && git pull
cd ~/frappe-bench
bench --site yoursite.local migrate
bench build --app ghana_payroll
bench restart
```

### Uninstall

```bash
bench --site yoursite.local uninstall-app ghana_payroll
```

Payroll data and custom fields are left intact; only the print format and
workspace are removed.

---

## Configuration

Everything lives in **Ghana Payroll Settings** (search the awesomebar).

1. **Enable Ghana PAYE Engine** — the master switch. Untick it and Salary Slips
   fall straight back to ERPNext's standard annualised engine.
2. **SSNIT rates** — employee 5.5%, employer 13%, and the Tier 1 / Tier 2 split.
3. **Insurable earnings limits** — optional floor and ceiling on the SSNIT base.
4. **Provident Fund rates** — employee 10%, employer 5%.
5. **Reliefs & rounding** — optional cap on how much pension contribution is
   deductible from chargeable income.
6. **Salary Component Mapping** — which components the app writes to. Created
   automatically on install:
   - `SSNIT Employee`, `Provident Fund Employee`, `PAYE` (real deductions)
   - `SSNIT Employer`, `Provident Fund Employer` (statistical)
7. **Pensionable Components** — the earnings that form the SSNIT/PF base.
   Defaults to `Basic`. Add housing or transport here if your scheme treats them
   as pensionable.
8. **Tax Exempt Components** — earnings excluded from chargeable income.
9. **PAYE Graduated Bands** — each row is the **width** of a band, not a
   cumulative ceiling. The last row must be the `Exceeding` band.

### Salary Structure setup

Add these to your Salary Structure:

- **Earnings:** `Basic` (plus your allowances)
- **Deductions:** `SSNIT Employee`, `Provident Fund Employee`, `PAYE`,
  `SSNIT Employer`, `Provident Fund Employer`

Leave the amounts and formulas blank — the app overwrites them on every slip.
No Income Tax Slab is required.

### Employee setup

The app adds a **Ghana Statutory Details** section to Employee:
TIN, SSNIT number, Tier 2 scheme, and Monthly Tax Relief.

### Payslip

Set **Ghana Salary Slip** as the default print format:
Salary Slip → Menu → Customize → Default Print Format.

---

## How the override works

ERPNext projects annual income, applies annual slabs, then divides across the
remaining periods. Ghana taxes each month independently, so the app intercepts
the single point where the stock engine produces a tax figure:

```
GhanaSalarySlip.calculate_variable_based_on_taxable_salary()
    -> tax_engine.compute_payroll()
        -> tax_engine.compute_paye()   # walks the monthly bands
```

Everything else in the slip lifecycle — payment days, loan repayment, rounding,
totals, submission, journal entries — is untouched.

SSNIT and Provident Fund figures are derived from the pensionable base rather
than read off the deduction rows, so PAYE does not depend on the row order in
your Salary Structure. The statutory rows are written back after the stock
deduction pass and before totals are struck.

The same `compute_payroll()` function backs the calculator page, so a payslip
and the calculator can never disagree.

---

## Reports

| Report | Use |
|---|---|
| Ghana PAYE Monthly Return | Employer's monthly PAYE filing: gross, deductions, chargeable income, tax |
| Ghana SSNIT Contribution Schedule | Tier 1 / Tier 2 remittance split per employee |
| Ghana Provident Fund Schedule | Tier 3 employee and employer contributions |
| Ghana Payroll Summary | Full cost-to-company view with net payable |

All filter on company, date range, department, employee and document status.

---

## Project layout

```
ghana_payroll/
├── install.sh                      bench installer
├── pyproject.toml
└── ghana_payroll/
    ├── hooks.py                    override registration
    ├── install.py                  components, custom fields, defaults
    ├── tax_engine.py               all Ghana tax maths
    ├── report_utils.py             shared report queries
    ├── overrides/salary_slip.py    the ERPNext override
    ├── tests/test_tax_engine.py
    ├── templates/print_formats/    Ghana payslip
    └── ghana_payroll/
        ├── doctype/                Settings, Tax Bracket, Component map
        ├── page/                   PAYE Calculator
        └── report/                 4 payroll reports
```

---

## Notes and limitations

- Rates ship as configuration and are correct as of the 2026 schedule, but you
  are responsible for keeping them current with GRA and SSNIT publications.
- The bonus concession is a simplified monthly proxy for an annual rule. Review
  it against your auditor's treatment before enabling it.
- Overtime concessionary rates, provisional/final tax on secondary employment,
  and non-cash benefit valuation are not implemented.
- This is payroll software, not tax advice. Have a Ghanaian tax practitioner
  review your configuration before your first live run.

## License

MIT
