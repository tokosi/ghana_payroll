#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Ghana Payroll - installer for ERPNext v16 (Community)
#
#   ./install.sh <site-name> [path-to-app]
#
# Example:
#   ./install.sh erp.mycompany.gh
#   ./install.sh erp.mycompany.gh /home/frappe/ghana_payroll
# ---------------------------------------------------------------------------
set -euo pipefail

SITE="${1:-}"
APP_PATH="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
APP_NAME="ghana_payroll"

if [[ -z "$SITE" ]]; then
	echo "Usage: ./install.sh <site-name> [path-to-app]"
	exit 1
fi

if [[ ! -f "sites/common_site_config.json" ]]; then
	echo "ERROR: run this from your frappe-bench directory (e.g. cd ~/frappe-bench)."
	exit 1
fi

echo "==> Checking prerequisites"
for dep in erpnext hrms; do
	if [[ ! -d "apps/$dep" ]]; then
		echo "ERROR: '$dep' is not installed in this bench. Install it first:"
		echo "       bench get-app $dep && bench --site $SITE install-app $dep"
		exit 1
	fi
done

if [[ ! -d "apps/$APP_NAME" ]]; then
	echo "==> Fetching app from $APP_PATH"
	bench get-app "$APP_NAME" "$APP_PATH"
else
	echo "==> App already present in apps/$APP_NAME"
fi

echo "==> Installing on site: $SITE"
bench --site "$SITE" install-app "$APP_NAME"

echo "==> Running migrations"
bench --site "$SITE" migrate

echo "==> Building assets"
bench build --app "$APP_NAME"

echo "==> Clearing cache"
bench --site "$SITE" clear-cache
bench --site "$SITE" clear-website-cache

echo "==> Restarting"
bench restart || echo "    (bench restart skipped - not running under supervisor)"

cat <<'DONE'

============================================================
 Ghana Payroll installed.

 Next steps:
   1. Open  Ghana Payroll Settings  and confirm the rates and
      graduated bands against the current GRA schedule.
   2. Add the Ghana components to your Salary Structure:
        Earnings   : Basic
        Deductions : SSNIT Employee, Provident Fund Employee, PAYE,
                     SSNIT Employer, Provident Fund Employer
   3. Set the Ghana Salary Slip print format as default on
      Salary Slip.
   4. Try the Ghana PAYE Calculator page to sanity-check figures.
============================================================
DONE
