"""Integration checks for the entirely synthetic V1.1 public demo fixtures."""

from decimal import Decimal
from pathlib import Path
import sqlite3

import pandas as pd

from src.services.appfolio_importer import HEADERS, parse_pdf as parse_owner
from src.services.financial_report import monthly_report
from src.services.mortgage_importer import parse_pdf as parse_mortgage, save_to_sqlite

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
OWNER_PDFS = sorted(EXAMPLES.glob("demo_owner_statement_2026_*.pdf"))
MORTGAGE_PDF = EXAMPLES / "demo_mortgage_payment_history_2026.pdf"


def test_synthetic_mortgage_events_reconcile_and_deduplicate(tmp_path):
    events = parse_mortgage(MORTGAGE_PDF)
    payments = [e for e in events if e["event_type"] == "mortgage_payment"]
    disbursements = [e for e in events if e["event_type"] == "escrow_disbursement"]
    assert len(payments) == 6
    assert len(disbursements) == 2
    assert {e["category"] for e in disbursements} == {"property_tax", "hazard_insurance"}
    for e in payments:
        assert e["principal_paid"] + e["interest_paid"] + e["escrow_contribution"] == e["payment_amount"]
    assert sum((e["payment_amount"] for e in payments), Decimal(0)) == Decimal("6770.70")
    db = tmp_path / "mortgage.sqlite"
    assert save_to_sqlite(events, db) == 8
    assert save_to_sqlite(events, db) == 0
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM mortgage_events").fetchone()[0] == 8


def test_full_synthetic_demo_actual_cash_flow(tmp_path):
    assert len(OWNER_PDFS) == 6
    rows = []
    for pdf in OWNER_PDFS:
        extracted, _ = parse_owner(pdf)  # Each statement is validated by its importer.
        rows.extend(extracted)

    db = tmp_path / "owner.sqlite"
    cols = ", ".join(
        f'"{key}" ' + ("REAL" if key in ("income", "expense", "amount", "statement_balance") else "TEXT")
        for key in HEADERS
    )
    with sqlite3.connect(db) as conn:
        conn.execute(f"CREATE TABLE transactions ({cols})")
        names = ", ".join(f'"{key}"' for key in HEADERS)
        placeholders = ", ".join("?" for _ in HEADERS)
        conn.executemany(
            f"INSERT INTO transactions ({names}) VALUES ({placeholders})",
            [[row[key] for key in HEADERS] for row in rows],
        )

    report = monthly_report(db_path=db)
    assert len(report) == 6
    mortgage = pd.DataFrame(parse_mortgage(MORTGAGE_PDF))
    mortgage = mortgage.loc[mortgage["event_type"].eq("mortgage_payment")].copy()
    mortgage["month"] = mortgage["effective_date"].str[:7]
    payments = mortgage.groupby("month", as_index=False)["payment_amount"].sum()
    merged = report.merge(payments, on="month", how="inner")
    assert len(merged) == 6
    merged["actual_cash_flow"] = merged["owner_distributions"] - merged["payment_amount"].astype(float)
    assert round(merged["actual_cash_flow"].sum(), 2) == 4475.30
    assert round(merged.loc[merged["month"].eq("2026-07"), "actual_cash_flow"].iloc[0], 2) == -349.95
