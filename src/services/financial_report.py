"""Financial reporting for imported property-management statements."""

import os
from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "local_data" / "production_verified" / "nesiaos.sqlite"


def monthly_report(db_path=None):
    """Calculate monthly rental operating performance.

    Set NESIAOS_DB_PATH to use a different database, such as a synthetic demo.
    An explicitly provided db_path overrides the environment variable.
    """
    if db_path is None:
        db_path = os.environ.get("NESIAOS_DB_PATH") or DEFAULT_DB_PATH
    db_path = Path(db_path).expanduser()
    if not db_path.is_file():
        raise FileNotFoundError(
            f"No financial database found at {db_path}. "
            "Import an example PDF or set NESIAOS_DB_PATH to an existing SQLite database."
        )

    with sqlite3.connect(db_path) as conn:
        transactions = pd.read_sql_query("SELECT * FROM transactions", conn)

    if transactions.empty:
        raise ValueError("No transactions found in database.")

    transactions["month"] = transactions["statement_start"].str[:7]
    if transactions["flow_type"].isin(["unknown"]).any():
        raise ValueError("Unclassified transactions found. Review importer.")

    transactions["operating_income"] = transactions["income"].where(
        transactions["flow_type"] == "income", 0
    )
    transactions["operating_expenses"] = transactions["expense"].where(
        transactions["flow_type"] == "operating_expense", 0
    )
    transactions["owner_distributions"] = transactions["expense"].where(
        transactions["flow_type"] == "transfer", 0
    )

    report = transactions.groupby("month", as_index=False).agg(
        operating_income=("operating_income", "sum"),
        operating_expenses=("operating_expenses", "sum"),
        owner_distributions=("owner_distributions", "sum"),
    )
    report["operating_cash_flow"] = (
        report["operating_income"] - report["operating_expenses"]
    )
    return report.round(2)


if __name__ == "__main__":
    report = monthly_report()
    print("\\nNESIAOS MONTHLY PROPERTY REPORT\\n")
    print(report.to_string(index=False))
