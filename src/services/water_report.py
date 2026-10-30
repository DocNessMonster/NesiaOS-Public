"""Water charges, confirmed owner payments, and AppFolio utility receipts."""
import json
import sqlite3
from pathlib import Path

import pandas as pd

COLUMNS = ['bill_id', 'bill_date', 'due_date', 'service_start', 'service_end',
           'water', 'wastewater', 'solid_waste', 'current_charges', 'balance_forward',
           'adjustments', 'total_due', 'payment_date', 'payment_amount']


def read_bills(db_path):
    path = Path(db_path).resolve()
    if not path.is_file():
        return pd.DataFrame(columns=COLUMNS)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='water_bills'").fetchone():
            raise ValueError('Water database is missing its bill table')
        rows = pd.read_sql_query('SELECT * FROM water_bills', conn)
    records = []
    for row in rows.to_dict('records'):
        details = json.loads(row['details_json'])
        result = {k: details.get(k) for k in COLUMNS}
        result.update(bill_id=row['bill_id'], payment_date=row['payment_date'])
        for key in ('water', 'wastewater', 'solid_waste', 'current_charges', 'balance_forward', 'total_due'):
            result[key] = float(details[key])
        result['adjustments'] = round(result['total_due'] - result['balance_forward'] - result['current_charges'], 2)
        payment_cents = row.get('payment_amount_cents')
        result['payment_amount'] = float(payment_cents) / 100 if pd.notna(payment_cents) else None
        if result['payment_date'] and result['payment_amount'] is None:
            raise ValueError('A recorded water payment is missing its confirmed amount')
        records.append(result)
    return pd.DataFrame(records, columns=COLUMNS).sort_values('bill_date')


def monthly_water_report(water_db, owner_db):
    bills = read_bills(water_db)
    records = {}
    def entry(month):
        return records.setdefault(month, {'month': month, 'water_billed': 0.0,
            'water_paid': 0.0, 'utility_reimbursements': 0.0, 'unconfirmed_bills': 0})
    for row in bills.to_dict('records'):
        item = entry(row['bill_date'][:7])
        item['water_billed'] += row['current_charges']
        if not row['payment_date']:
            item['unconfirmed_bills'] += 1
        else:
            entry(row['payment_date'][:7])['water_paid'] += row['payment_amount']
    with sqlite3.connect(Path(owner_db).resolve().as_uri() + '?mode=ro', uri=True) as conn:
        for month, amount in conn.execute('''SELECT substr(statement_start,1,7), SUM(income)
            FROM transactions WHERE category='utility_reimbursement' AND flow_type='income'
            GROUP BY substr(statement_start,1,7)'''):
            entry(month)['utility_reimbursements'] += float(amount or 0)
    columns = ['month', 'water_billed', 'water_paid', 'utility_reimbursements', 'unconfirmed_bills']
    return pd.DataFrame(sorted(records.values(), key=lambda r: r['month']), columns=columns).round(2)
