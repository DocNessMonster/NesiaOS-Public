"""Import a one-page mortgage payment-history PDF into a local SQLite database.

This importer handles the transposed table used by the sample lender statement.
No account details are required, stored, or included in this script.

Usage:
    python -m src.services.mortgage_importer local_data/mortgage/mortgage_history_2026.pdf --db local_data/mortgage/mortgage.sqlite
"""

import argparse
import hashlib
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path


# The PDF's columns appear as rows, with each cell's characters reversed.
ROWS = {
    "effective_date": 15,
    "due_date": 14,
    "description": 13,
    "total": 12,
    "principal": 11,
    "principal_balance": 10,
    "interest": 9,
    "escrow": 8,
    "escrow_balance": 7,
}

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS mortgage_events (
    event_id TEXT PRIMARY KEY,
    effective_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    event_type TEXT NOT NULL,
    category TEXT NOT NULL,
    payment_amount REAL NOT NULL,
    principal_paid REAL NOT NULL,
    interest_paid REAL NOT NULL,
    escrow_contribution REAL NOT NULL,
    escrow_disbursement REAL NOT NULL,
    principal_balance REAL NOT NULL,
    escrow_balance REAL NOT NULL
)
"""


def money(text):
    """Parse dollar amounts, including negatives formatted like ($909.00)."""
    value = str(text or "").strip().replace("$", "").replace(",", "")
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    return Decimal(value)


def field(table, row, col):
    return (table[row][col] or "")[::-1].replace("\n", " ").strip()


def parse_pdf(pdf_path):
    """Return normalized rows for mortgage payments and escrow disbursements."""
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError("Expected a one-page mortgage payment history")
        tables = pdf.pages[0].extract_tables()

    table = next((t for t in tables if len(t) >= 16 and len(t[0]) > 1
                  and "effective" in field(t, 15, 0).lower()), None)
    if table is None:
        raise ValueError("Mortgage payment table not found or unsupported layout")

    events = []
    for col in range(1, len(table[0])):
        raw = {key: field(table, row, col) for key, row in ROWS.items()}
        if not raw["effective_date"]:
            continue

        effective_date = datetime.strptime(raw["effective_date"], "%m/%d/%y").date().isoformat()
        due_date = datetime.strptime(raw["due_date"], "%m/%d/%y").date().isoformat()
        total = money(raw["total"])
        principal = abs(money(raw["principal"]))
        interest = money(raw["interest"])
        escrow = money(raw["escrow"])
        description = raw["description"].lower()

        if "disbursement" in description:
            event_type = "escrow_disbursement"
            category = ("property_tax" if "tax" in description else
                        "hazard_insurance" if "insurance" in description else
                        "unclassified_escrow_disbursement")
            if total >= 0 or escrow >= 0 or principal != 0 or interest != 0 or total != escrow:
                raise ValueError(f"Escrow disbursement did not reconcile: {effective_date}")
            payment_amount = Decimal("0")
            escrow_contribution = Decimal("0")
            escrow_disbursement = -escrow
        elif "payment" in description:
            event_type = "mortgage_payment"
            category = "regular_payment"
            if total <= 0 or principal + interest + escrow != total:
                raise ValueError(f"Mortgage payment did not reconcile: {effective_date}")
            payment_amount = total
            escrow_contribution = escrow
            escrow_disbursement = Decimal("0")
        else:
            raise ValueError(f"Unknown mortgage event: {effective_date}")

        # Stable within one loan's payment log: a repeated import won't double-count.
        identity = "|".join([effective_date, due_date, event_type, str(total),
                             str(principal), str(interest), str(escrow)])
        events.append({
            "event_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
            "effective_date": effective_date,
            "due_date": due_date,
            "event_type": event_type,
            "category": category,
            "payment_amount": payment_amount,
            "principal_paid": principal,
            "interest_paid": interest,
            "escrow_contribution": escrow_contribution,
            "escrow_disbursement": escrow_disbursement,
            "principal_balance": money(raw["principal_balance"]),
            "escrow_balance": money(raw["escrow_balance"]),
        })

    if not events:
        raise ValueError("No transactions found")
    return events


def save_to_sqlite(events, db_path):
    """Safely import rows, skipping events already present."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(events[0])
    placeholders = ", ".join("?" for _ in columns)
    query = f"INSERT OR IGNORE INTO mortgage_events ({', '.join(columns)}) VALUES ({placeholders})"
    with sqlite3.connect(db_path) as connection:
        connection.execute(CREATE_TABLE)
        before = connection.total_changes
        connection.executemany(query, [
            [str(e[k]) if isinstance(e[k], Decimal) else e[k] for k in columns]
            for e in events
        ])
        added = connection.total_changes - before
    return added


def main():
    parser = argparse.ArgumentParser(description="Import local mortgage payment history")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--db", required=True, type=Path)
    args = parser.parse_args()
    events = parse_pdf(args.pdf)
    added = save_to_sqlite(events, args.db)
    payments = sum(e["event_type"] == "mortgage_payment" for e in events)
    disbursements = sum(e["event_type"] == "escrow_disbursement" for e in events)
    print(f"PASS: {len(events)} events ({payments} payments, {disbursements} escrow disbursements)")
    print(f"Saved {added} new events to {args.db}")


if __name__ == "__main__":
    main()
