"""Import text-based ABCWUA bills; amounts billed are separate from payments."""
import argparse
import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / 'local_data' / 'water' / 'water.sqlite'


def parse_pdf(path):
    import pdfplumber
    path = Path(path)
    with pdfplumber.open(path) as pdf:
        text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    text = re.sub(r'\s+', '', text)

    def find(pattern):
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f'Required bill field missing: {pattern}')
        return match.group(1)

    def iso_date(value):
        return datetime.strptime(value.replace('-', '/'), '%m/%d/%Y').date().isoformat()

    def amount(label):
        return Decimal(find(label + r'\$?(-?[\d,]+\.\d{2})').replace(',', ''))

    period = re.search(r'WaterResidentialCity:?(\d{2}-\d{2}-\d{4})-(\d{2}-\d{2}-\d{4})', text)
    if not period:
        raise ValueError('Service period missing')
    subtotals = [Decimal(value.replace(',', '')) for value in re.findall(r'Subtotal\$?([\d,]+\.\d{2})', text)]
    charges = amount('CurrentCharges')
    if len(subtotals) != 3 or sum(subtotals) != charges:
        raise ValueError('Bill subtotals need review; import stopped')
    # Adjustments affect the total due, not the current service subtotals.
    adjustments = amount(r'TotalAdjustments\(Billed&Unbilled\)')
    if amount('BalanceForward') + adjustments + charges != amount('TotalAmountDue'):
        raise ValueError('Bill balance and adjustments do not reconcile')
    start, end = map(iso_date, period.groups())
    if start > end:
        raise ValueError('Service period dates are reversed')
    return {
        'provider': 'ABCWUA',
        'account_number': find(r'AccountNumber:(\d+)'),
        'bill_date': iso_date(find(r'BillingDate:(\d{2}/\d{2}/\d{4})')),
        'due_date': iso_date(find(r'DueDate:(\d{2}/\d{2}/\d{4})')),
        'service_start': start, 'service_end': end,
        'water': str(subtotals[0]), 'wastewater': str(subtotals[1]),
        'solid_waste': str(subtotals[2]), 'current_charges': str(charges),
        'balance_forward': str(amount('BalanceForward')),
        'total_due': str(amount('TotalAmountDue')),
        'reimbursable_amount': str(charges),
        'payment_date': None, 'source_file': path.name,
    }


def ensure_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS water_bills (
        bill_id TEXT PRIMARY KEY, bill_date TEXT NOT NULL, due_date TEXT NOT NULL,
        current_charges_cents INTEGER NOT NULL, details_json TEXT NOT NULL,
        source_file TEXT NOT NULL, payment_date TEXT)''')
    columns = {row[1] for row in conn.execute('PRAGMA table_info(water_bills)')}
    if 'payment_amount_cents' not in columns:
        conn.execute('ALTER TABLE water_bills ADD COLUMN payment_amount_cents INTEGER')


def save_bill(bill, db_path=DEFAULT_DB):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    identity = '|'.join(bill[k] for k in ('provider', 'account_number', 'bill_date', 'service_start', 'service_end'))
    bill_id = hashlib.sha256(identity.encode()).hexdigest()
    details = {k: v for k, v in bill.items() if k not in ('source_file', 'payment_date')}
    payload = json.dumps(details, sort_keys=True)
    cents = int(Decimal(bill['current_charges']) * 100)
    with sqlite3.connect(db_path) as conn:
        ensure_schema(conn)
        existing = conn.execute('SELECT details_json FROM water_bills WHERE bill_id = ?', (bill_id,)).fetchone()
        if existing:
            if existing[0] != payload:
                raise ValueError('This bill already exists with different details; review before replacing')
            return 'SKIPPED: bill already imported'
        conn.execute('''INSERT INTO water_bills
            (bill_id, bill_date, due_date, current_charges_cents, details_json, source_file, payment_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (bill_id, bill['bill_date'], bill['due_date'], cents, payload, bill['source_file'], None))
    return 'SAVED: new water bill'


def record_payment(db_path, bill_id, paid_on, amount):
    """Record one confirmed full payment per bill; never infer it from autopay."""
    paid_on = date.fromisoformat(str(paid_on)).isoformat()
    amount = Decimal(str(amount))
    if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal('.01')):
        raise ValueError('Payment must be positive with at most two decimal places')
    cents = int(amount * 100)
    with sqlite3.connect(db_path) as conn:
        ensure_schema(conn)
        row = conn.execute('SELECT payment_date, payment_amount_cents FROM water_bills WHERE bill_id = ?', (bill_id,)).fetchone()
        if row is None:
            raise ValueError('Bill not found')
        if row[0] is not None:
            if row == (paid_on, cents):
                return
            raise ValueError('A different payment is already recorded; review it before changing')
        conn.execute('UPDATE water_bills SET payment_date = ?, payment_amount_cents = ? WHERE bill_id = ?',
                     (paid_on, cents, bill_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    bill = parse_pdf(args.pdf)
    print(json.dumps(bill, indent=2))
    print(save_bill(bill, args.db))


if __name__ == '__main__':
    main()
