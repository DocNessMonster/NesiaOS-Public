"""Synthetic water-bank reconciliation tests. Never access personal bank records."""
import json
import sqlite3

import pytest

from src.services.water_importer import ensure_schema, record_payment
from src.services.water_reconciliation import (
    confirm_bank_payment, read_confirmed_payments, bill_reconciliation,
)
from src.services.water_report import monthly_water_report


def fixtures(tmp_path):
    water = tmp_path / "water.sqlite"
    owner = tmp_path / "owner.sqlite"
    with sqlite3.connect(water) as db:
        ensure_schema(db)
        for bill_id, month, charge in [
            ("may", "2026-05", 9632),
            ("june", "2026-06", 11188),
            ("july", "2026-07", 10176),
        ]:
            bill_date = f"{month}-15"
            details = dict(
                bill_date=bill_date, due_date=f"{month}-28",
                water=str(charge / 100), wastewater="0", solid_waste="0",
                current_charges=str(charge / 100), balance_forward="0",
                total_due=str(charge / 100),
            )
            db.execute(
                "INSERT INTO water_bills (bill_id, bill_date, due_date, "
                "current_charges_cents, details_json, source_file, payment_date) "
                "VALUES (?,?,?,?,?,?,NULL)",
                (bill_id, bill_date, f"{month}-28", charge,
                 json.dumps(details), "fictional.pdf"),
            )
    with sqlite3.connect(owner) as db:
        db.execute("CREATE TABLE transactions (statement_start TEXT, category TEXT, "
                   "flow_type TEXT, income REAL)")
    return water, owner


def test_combined_bank_payment_counts_once(tmp_path):
    water, owner = fixtures(tmp_path)
    confirm_bank_payment(
        water, "withdrawal-july", "2026-07-03", "208.20",
        "fictional-bank-row-1", {"may": "96.32", "june": "111.88"},
    )
    payments = read_confirmed_payments(water)
    assert payments == [{"paid_on": "2026-07-03", "amount_cents": 20820}]
    balances = {row["bill_id"]: row["remaining_cents"]
                for row in bill_reconciliation(water)}
    assert balances == {"may": 0, "june": 0, "july": 10176}
    monthly = monthly_water_report(water, owner).set_index("month")
    assert monthly.loc["2026-07", "water_paid"] == 208.20
    assert monthly.loc["2026-05", "water_paid"] == 0
    assert monthly.loc["2026-06", "unconfirmed_bills"] == 0


def test_overallocation_rejected_without_bank_entry(tmp_path):
    water, _ = fixtures(tmp_path)
    with pytest.raises(ValueError, match="exceeds bill charges"):
        confirm_bank_payment(
            water, "bad", "2026-07-03", "209.64",
            "bad-reference", {"may": "97.76", "june": "111.88"},
        )
    assert read_confirmed_payments(water) == []


def test_unbalanced_and_duplicate_bank_rows_rejected(tmp_path):
    water, _ = fixtures(tmp_path)
    with pytest.raises(ValueError, match="must equal"):
        confirm_bank_payment(
            water, "unbalanced", "2026-07-03", "208.20",
            "row-unbalanced", {"may": "96.32"},
        )
    confirm_bank_payment(
        water, "withdrawal-1", "2026-07-03", "96.32",
        "unique-ref", {"may": "96.32"},
    )
    with pytest.raises(sqlite3.IntegrityError):
        confirm_bank_payment(
            water, "withdrawal-2", "2026-07-04", "101.76",
            "unique-ref", {"july": "101.76"},
        )
    assert len(read_confirmed_payments(water)) == 1


def test_legacy_and_new_payment_cannot_overlap(tmp_path):
    water, _ = fixtures(tmp_path)
    record_payment(water, "july", "2026-08-04", "101.76")
    with pytest.raises(ValueError, match="legacy"):
        confirm_bank_payment(
            water, "wrong", "2026-08-04", "101.76",
            "bank-wrong", {"july": "101.76"},
        )
    confirm_bank_payment(
        water, "bank-may", "2026-07-03", "96.32",
        "bank-may-ref", {"may": "96.32"},
    )
    with pytest.raises(ValueError, match="bank payment allocations"):
        record_payment(water, "may", "2026-07-03", "96.32")
    assert sum(p["amount_cents"] for p in read_confirmed_payments(water)) == 19808


def test_partial_payment_then_second_payment(tmp_path):
    water, _ = fixtures(tmp_path)
    confirm_bank_payment(water, "partial", "2026-06-01", "40.00",
                         "partial-ref", {"may": "40.00"})
    assert next(x for x in bill_reconciliation(water)
                if x["bill_id"] == "may")["remaining_cents"] == 5632
    confirm_bank_payment(water, "balance", "2026-07-03", "56.32",
                         "balance-ref", {"may": "56.32"})
    assert next(x for x in bill_reconciliation(water)
                if x["bill_id"] == "may")["remaining_cents"] == 0
