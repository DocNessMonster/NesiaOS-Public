"""Use fictional transactions to verify narrow tax-expense classifications."""
import sqlite3

from src.services.schedule_e_report import schedule_e_report


def test_documented_alarm_and_linked_sales_tax(tmp_path):
    owner, mortgage, water, capital = (
        tmp_path / "owner.sqlite", tmp_path / "mortgage.sqlite",
        tmp_path / "missing-water.sqlite", tmp_path / "missing-capital.sqlite"
    )
    with sqlite3.connect(owner) as con:
        con.execute(
            "CREATE TABLE transactions (date TEXT, description TEXT, "
            "category TEXT, flow_type TEXT, income REAL, expense REAL)"
        )
        rows = [
            ("2026-04-20", "HVAC - Service - 28755-1", "hvac", "operating_expense", 0, 226.91),
            ("2026-04-20", "Tax - Sales - Service - 28755-1", "sales_tax", "operating_expense", 0, 2.12),
            ("2026-05-08", "Smoke Alarm Is Not Turning Off - 28823-1", "safety_equipment", "operating_expense", 0, 252.37),
            ("2026-05-08", "Tax - Sales - Smoke Alarm - 28823-1", "sales_tax", "operating_expense", 0, 2.36),
            ("2026-05-20", "Renewal Fee", "leasing_fee", "operating_expense", 0, 205),
            ("2026-05-20", "Tax - Sales", "sales_tax", "operating_expense", 0, 13.25),
            ("2026-06-10", "Electrical - 29407-1", "electrical", "operating_expense", 0, 314.80),
            ("2026-06-10", "Tax - Sales - 29407-1", "sales_tax", "operating_expense", 0, 2.95),
            ("2026-07-10", "Tree service - 29617-1", "landscaping", "operating_expense", 0, 1287),
            ("2026-07-10", "Tax - Sales - 29617-1", "sales_tax", "operating_expense", 0, 12.04),
            ("2026-08-27", "Tree trimming - 30555-1", "landscaping", "operating_expense", 0, 280.31),
            ("2026-08-27", "Toilet - 30629-1", "plumbing", "operating_expense", 0, 171.58),
            ("2026-08-27", "Tax - Sales - Toilet - 30629-1", "sales_tax", "operating_expense", 0, 1.61),
        ]
        con.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?)", rows)
    with sqlite3.connect(mortgage) as con:
        con.execute(
            "CREATE TABLE mortgage_events (effective_date TEXT, event_type TEXT, "
            "category TEXT, interest_paid REAL, escrow_disbursement REAL)"
        )
    result = schedule_e_report(2026, owner, mortgage, water, capital)
    assert round(result["lines"][14], 2) == 974.70
    assert round(result["lines"][7], 2) == 1579.35
    assert round(result["lines"][8], 2) == 218.25
    assert not any("sales_tax" in item or "safety_equipment" in item for item in result["review"])


def test_ambiguous_tax_and_new_safety_installation_remain_for_review(tmp_path):
    owner, mortgage = tmp_path / "owner.sqlite", tmp_path / "mortgage.sqlite"
    with sqlite3.connect(owner) as con:
        con.execute(
            "CREATE TABLE transactions (date TEXT, description TEXT, "
            "category TEXT, flow_type TEXT, income REAL, expense REAL)"
        )
        con.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?)", [
            ("2026-06-01", "New building-wide alarm system", "safety_equipment", "operating_expense", 0, 5000),
            ("2026-06-01", "Repair one", "plumbing", "operating_expense", 0, 100),
            ("2026-06-01", "Repair two", "electrical", "operating_expense", 0, 100),
            ("2026-06-01", "Tax - Sales", "sales_tax", "operating_expense", 0, 10),
        ])
    with sqlite3.connect(mortgage) as con:
        con.execute(
            "CREATE TABLE mortgage_events (effective_date TEXT, event_type TEXT, "
            "category TEXT, interest_paid REAL, escrow_disbursement REAL)"
        )
    report = schedule_e_report(
        2026, owner, mortgage, tmp_path / "missing-water.sqlite",
        tmp_path / "missing-capital.sqlite"
    )
    assert any("safety_equipment" in issue for issue in report["review"])
    assert any("sales_tax" in issue for issue in report["review"])
