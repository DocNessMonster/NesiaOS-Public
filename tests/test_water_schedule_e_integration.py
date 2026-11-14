"""Schedule E counts dated bank withdrawals once, regardless of bill allocations."""
import sqlite3

from src.services.water_importer import ensure_schema
from src.services.water_reconciliation import confirm_bank_payment
from src.services.schedule_e_report import schedule_e_report


def test_schedule_e_uses_combined_withdrawal_date_once(tmp_path):
    owner = tmp_path / "owner.sqlite"
    mortgage = tmp_path / "mortgage.sqlite"
    water = tmp_path / "water.sqlite"
    capital = tmp_path / "missing_capital.sqlite"

    with sqlite3.connect(owner) as conn:
        conn.execute("CREATE TABLE transactions "
                     "(date TEXT, category TEXT, flow_type TEXT, "
                     "income REAL, expense REAL, description TEXT)")
        conn.execute("INSERT INTO transactions VALUES "
                     "('2026-07-01','rent_income','income',1000,0,'Rent')")
    with sqlite3.connect(mortgage) as conn:
        conn.execute("CREATE TABLE mortgage_events "
                     "(effective_date TEXT, event_type TEXT, category TEXT, "
                     "interest_paid REAL, escrow_disbursement REAL)")
    with sqlite3.connect(water) as conn:
        ensure_schema(conn)
        for key, month, charge in [
            ("may", "2026-05", 9632),
            ("june", "2026-06", 11188),
        ]:
            conn.execute(
                "INSERT INTO water_bills "
                "(bill_id, bill_date, due_date, current_charges_cents, "
                "details_json, source_file, payment_date) "
                "VALUES (?, ?, ?, ?, '{}', 'synthetic.pdf', NULL)",
                (key, month + "-15", month + "-28", charge),
            )
    confirm_bank_payment(
        water, "combined", "2026-07-03", "208.20",
        "synthetic-bank-ref", {"may": "96.32", "june": "111.88"},
    )
    report = schedule_e_report(2026, owner, mortgage, water, capital)
    assert report["lines"][17] == 208.20
    assert report["known_expenses_excluding_depreciation"] == 208.20
    assert report["provisional_difference"] == 791.80
    assert not any("Water bill" in entry for entry in report["review"])
