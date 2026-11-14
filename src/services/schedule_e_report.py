"""Read-only, preliminary Schedule E worksheet. Not a tax return."""
import sqlite3
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from src.services.financial_report import DEFAULT_DB_PATH
from src.services.capital_report import DEFAULT_CAPITAL_DB, list_improvements
from src.services.water_reconciliation import read_confirmed_payments

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MORTGAGE_DB = ROOT / "local_data/mortgage/mortgage.sqlite"
DEFAULT_WATER_DB = ROOT / "local_data/water/water.sqlite"

# Unknown categories are surfaced for review, not silently deducted.
APPFOLIO_LINES = {
    "rent_income": 3, "utility_reimbursement": 3,
    "landscaping_reimbursement": 3, "landscaping": 7,
    "leasing_fee": 8, "management_fee": 11, "plumbing": 14,
    "hvac": 14, "electrical": 14, "safety_equipment": None,
    "sales_tax": None,
}
LABELS = {
    3: "Rents received including reimbursements",
    7: "Cleaning and maintenance", 8: "Commissions",
    9: "Insurance", 11: "Management fees", 12: "Mortgage interest",
    14: "Repairs", 16: "Taxes", 17: "Utilities",
}



WORK_ORDER_RE = re.compile(r"\b\d{5,}-\d+\b")


def classify_safety_expense(description):
    """Auto-classify documented alarm repair only; other equipment needs review."""
    text = description.lower()
    if ("smoke alarm" in text and
            ("not turning off" in text or "repair" in text or "replac" in text)):
        return 14
    return None


def classify_sales_tax(tax_row, expense_rows):
    """Follow exactly one identifiable same-date underlying operating expense."""
    description = str(tax_row.get("description") or "")
    order_ids = WORK_ORDER_RE.findall(description)
    candidates = [
        row for row in expense_rows
        if row["date"] == tax_row["date"] and
        row["category"] != "sales_tax"
        and row.get("flow_type") == "operating_expense"
    ]
    if order_ids:
        candidates = [
            row for row in candidates
            if any(identifier in str(row.get("description") or "")
                   for identifier in order_ids)
        ]
    elif "Tax - Sales" == description.strip():
        # Only unreferenced tax with exactly one underlying expense on the date.
        pass
    else:
        # An identified tax must not be attached by date alone.
        return None
    if len(candidates) != 1:
        return None
    underlying = candidates[0]
    if underlying["category"] == "safety_equipment":
        return classify_safety_expense(str(underlying.get("description") or ""))
    return APPFOLIO_LINES.get(underlying["category"])


def read_only_rows(path, sql):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Required database not found: {path}")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql)]


def decimal(value):
    return Decimal(str(value if value is not None else 0))


def schedule_e_report(year, owner_db=None, mortgage_db=None,
                      water_db=None, capital_db=None):
    """Build a provisional, single-property worksheet using payment dates."""
    year = int(year)
    if not 2000 <= year <= 2100:
        raise ValueError("Invalid tax year")
    prefix = f"{year}-"
    totals = defaultdict(lambda: Decimal("0"))
    review = []
    income = {"rent_income", "utility_reimbursement", "landscaping_reimbursement"}
    expense = set(APPFOLIO_LINES) - income

    appfolio_rows = read_only_rows(
        owner_db or DEFAULT_DB_PATH,
        "SELECT date, description, category, flow_type, income, expense FROM transactions",
    )
    operating_rows = [
        row for row in appfolio_rows
        if str(row["date"]).startswith(prefix) and
        row["flow_type"] == "operating_expense"
    ]
    for row in appfolio_rows:
        if not str(row["date"]).startswith(prefix):
            continue
        category, flow = row["category"], row["flow_type"]
        if category == "owner_distribution" and flow == "transfer":
            continue
        expected = ("income" if category in income else
                    "operating_expense" if category in expense else None)
        if flow != expected:
            review.append(f"Unclassified AppFolio transaction: {row['date']} {category}")
            continue
        amount = decimal(row["income"] if flow == "income" else row["expense"])
        if amount < 0:
            review.append(f"Negative amount requires review: {row['date']} {category}")
            continue
        line = APPFOLIO_LINES[category]
        if category == "safety_equipment":
            line = classify_safety_expense(str(row.get("description") or ""))
        elif category == "sales_tax":
            line = classify_sales_tax(row, operating_rows)
        if line is None:
            review.append(f"Expense category requires review: {row['date']} {category} ${amount:.2f}")
        else:
            totals[line] += amount

    for row in read_only_rows(
        mortgage_db or DEFAULT_MORTGAGE_DB,
        "SELECT effective_date, event_type, category, interest_paid, escrow_disbursement "
        "FROM mortgage_events",
    ):
        if not str(row["effective_date"]).startswith(prefix):
            continue
        if row["event_type"] == "mortgage_payment":
            totals[12] += decimal(row["interest_paid"])
        elif row["event_type"] == "escrow_disbursement":
            line = {"property_tax": 16, "hazard_insurance": 9}.get(row["category"])
            if line is None:
                review.append(f"Unclassified escrow event: {row['effective_date']}")
            else:
                totals[line] += decimal(row["escrow_disbursement"])
        else:
            review.append(f"Unknown mortgage event: {row['effective_date']}")

    water_path = Path(water_db or DEFAULT_WATER_DB)
    if water_path.is_file():
        for payment in read_confirmed_payments(water_path):
            if str(payment["paid_on"]).startswith(prefix):
                totals[17] += decimal(payment["amount_cents"]) / 100
        # Bills that still have an unpaid balance are explicitly identified.
        from src.services.water_reconciliation import bill_reconciliation
        for bill in bill_reconciliation(water_path):
            if (str(bill["bill_date"]).startswith(prefix)
                    and bill["remaining_cents"] > 0):
                review.append(f"Water bill has unpaid/unmatched balance: {bill['bill_date']}")
    else:
        review.append("Water database missing; expenses may be incomplete")

    capital_path = capital_db or DEFAULT_CAPITAL_DB
    assets = [
        asset for asset in list_improvements(capital_path)
        if str(asset["completion_date"]).startswith(prefix)
    ]
    capital_cost = sum(
        (decimal(asset["cost_cents"]) / 100 for asset in assets),
        Decimal("0"),
    )
    if assets:
        review.append("Capital improvement depreciation not calculated")
    review.extend([
        "Original building and prior-year depreciation not calculated",
        "Check tax treatment, complete year coverage, and additional owner-paid expenses",
    ])
    expenses_known = sum(
        (amount for line, amount in totals.items() if line != 3),
        Decimal("0"),
    )
    return {
        "year": year,
        "lines": {line: float(totals[line]) for line in LABELS},
        "labels": LABELS,
        "income": float(totals[3]),
        "known_expenses_excluding_depreciation": float(expenses_known),
        "provisional_difference": float(totals[3] - expenses_known),
        "capital_improvements": assets,
        "capital_spending": float(capital_cost),
        "review": sorted(set(review)),
        "filing_ready": False,
    }
