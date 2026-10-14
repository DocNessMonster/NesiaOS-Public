"""Test that financial reporting works with an isolated synthetic database."""

import sqlite3
from pathlib import Path

from src.services.appfolio_importer import HEADERS, parse_pdf
from src.services.financial_report import monthly_report


SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_owner_statement.pdf"


def test_monthly_report_from_synthetic_statement(tmp_path, monkeypatch):
    rows, _ = parse_pdf(SAMPLE)
    db = tmp_path / "demo.sqlite"
    columns = ", ".join(
        f'"{h}" ' + ("REAL" if h in ("income", "expense", "amount", "statement_balance") else "TEXT")
        for h in HEADERS
    )
    with sqlite3.connect(db) as connection:
        connection.execute(f"CREATE TABLE transactions ({columns})")
        names = ", ".join(f'"{h}"' for h in HEADERS)
        placeholders = ", ".join("?" for _ in HEADERS)
        connection.executemany(
            f"INSERT INTO transactions ({names}) VALUES ({placeholders})",
            [[row[h] for h in HEADERS] for row in rows],
        )

    monkeypatch.setenv("NESIAOS_DB_PATH", str(db))
    report = monthly_report()
    assert len(report) == 1
    month = report.iloc[0]
    assert month["operating_income"] == 2000.0
    assert month["operating_expenses"] == 325.0
    assert month["owner_distributions"] == 1675.0
    assert month["operating_cash_flow"] == 1675.0


def test_missing_demo_database_is_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("NESIAOS_DB_PATH", str(tmp_path / "missing.sqlite"))
    try:
        monthly_report()
    except FileNotFoundError as exc:
        assert "NESIAOS_DB_PATH" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing database")
