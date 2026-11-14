"""Validated water payment ledger: one bank withdrawal may cover multiple bills.

This module never guesses bank dates or silently modifies legacy confirmations.
All monetary values are stored as integer cents. Source CSVs stay private.
"""
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.services.water_importer import ensure_schema

CREATE_PAYMENTS = """
CREATE TABLE IF NOT EXISTS water_bank_payments (
    payment_id TEXT PRIMARY KEY,
    paid_on TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    source_reference TEXT NOT NULL UNIQUE
)
"""
CREATE_ALLOCATIONS = """
CREATE TABLE IF NOT EXISTS water_payment_allocations (
    payment_id TEXT NOT NULL REFERENCES water_bank_payments(payment_id),
    bill_id TEXT NOT NULL REFERENCES water_bills(bill_id),
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    PRIMARY KEY (payment_id, bill_id)
)
"""


def cents(value):
    amount = Decimal(str(value))
    scaled = amount * 100
    if not amount.is_finite() or amount <= 0 or scaled != scaled.to_integral_value():
        raise ValueError("Amount must be positive with at most two decimals")
    return int(scaled)


def confirm_bank_payment(db_path, payment_id, paid_on, amount, source_reference,
                         allocations):
    """Atomically save one bank withdrawal and its bill allocations.

    allocations: {bill_id: dollar_amount}; must account for the entire withdrawal.
    No legacy-confirmed bill may be allocated again. Multiple separate bank
    payments can partially cover a bill; total allocations cannot exceed charges.
    """
    date.fromisoformat(str(paid_on))
    if not payment_id or not source_reference or not allocations:
        raise ValueError("Payment ID, bank reference, and allocations are required")
    total_cents = cents(amount)
    alloc = {bill_id: cents(value) for bill_id, value in allocations.items()}
    if sum(alloc.values()) != total_cents:
        raise ValueError("Allocated amounts must equal bank withdrawal")
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"Water database not found: {path}")
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        ensure_schema(conn)
        conn.execute(CREATE_PAYMENTS)
        conn.execute(CREATE_ALLOCATIONS)
        # Read and validate everything before inserting.
        for bill_id, allocation in alloc.items():
            row = conn.execute(
                "SELECT current_charges_cents, payment_date FROM water_bills "
                "WHERE bill_id=?", (bill_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Unknown bill ID: {bill_id}")
            charge, legacy_paid = row
            if legacy_paid is not None:
                raise ValueError(f"Bill already has a legacy confirmed payment: {bill_id}")
            already = conn.execute(
                "SELECT COALESCE(SUM(amount_cents),0) "
                "FROM water_payment_allocations WHERE bill_id=?", (bill_id,)
            ).fetchone()[0]
            if already + allocation > charge:
                raise ValueError(f"Allocation exceeds bill charges: {bill_id}")
        conn.execute(
            "INSERT INTO water_bank_payments VALUES (?,?,?,?)",
            (payment_id, str(paid_on), total_cents, source_reference),
        )
        conn.executemany(
            "INSERT INTO water_payment_allocations VALUES (?,?,?)",
            [(payment_id, bill, amount) for bill, amount in alloc.items()],
        )


def read_confirmed_payments(db_path):
    """Return dated payments in cents, including legacy payments once each.

    Entries recorded through the new ledger and old bill confirmation method
    never overlap because confirm_bank_payment rejects already-paid legacy bills.
    """
    path = Path(db_path)
    if not path.is_file():
        return []
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        has_ledger = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='water_bank_payments'"
        ).fetchone()
        bank_rows = (
            conn.execute("SELECT paid_on, amount_cents FROM water_bank_payments")
            .fetchall() if has_ledger else []
        )
        legacy_rows = conn.execute(
            "SELECT payment_date, payment_amount_cents FROM water_bills "
            "WHERE payment_date IS NOT NULL"
        ).fetchall()
    if any(amount is None for _, amount in legacy_rows):
        raise ValueError("Legacy confirmed water payment missing amount")
    return [
        {"paid_on": paid_on, "amount_cents": int(amount)}
        for paid_on, amount in bank_rows + legacy_rows
    ]


def bill_reconciliation(db_path):
    """Return bill balances in cents without inferring payments from due dates."""
    path = Path(db_path)
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        has_ledger = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='water_payment_allocations'"
        ).fetchone()
        sql = (
            "SELECT b.bill_id, b.bill_date, b.current_charges_cents, "
            "b.payment_date, COALESCE(SUM(a.amount_cents),0) AS allocated_cents "
            "FROM water_bills b LEFT JOIN water_payment_allocations a "
            "ON b.bill_id=a.bill_id GROUP BY b.bill_id ORDER BY b.bill_date"
            if has_ledger else
            "SELECT bill_id, bill_date, current_charges_cents, payment_date, "
            "0 AS allocated_cents FROM water_bills ORDER BY bill_date"
        )
        rows = [dict(row) for row in conn.execute(sql)]
    for row in rows:
        row["remaining_cents"] = (
            0 if row["payment_date"] is not None else
            row["current_charges_cents"] - row["allocated_cents"]
        )
    return rows
