"""Exercise real import boundaries with completely fictional utility fixtures."""
import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.services.water_importer import parse_pdf, save_bill, record_payment
from src.services.water_report import read_bills, monthly_water_report
from streamlit_app import build_demo_databases, build_demo_water_database

ROOT = Path(__file__).resolve().parents[1]


def test_six_bills_and_continuation_page():
    bills = [parse_pdf(ROOT / 'examples' / f'demo_water_bill_2026_{m:02d}.pdf') for m in range(4, 10)]
    assert sum(Decimal(b['current_charges']) for b in bills) == Decimal('540.00')
    assert bills[3]['solid_waste'] == '20.00'  # July's trash is on page two.
    assert bills[0]['service_start'] == '2026-03-17'
    assert all(b['payment_date'] is None for b in bills)


def test_renamed_duplicate_and_changed_bill(tmp_path):
    bill = parse_pdf(ROOT / 'examples' / 'demo_water_bill_2026_04.pdf')
    db = tmp_path / 'water.sqlite'
    assert save_bill(bill, db).startswith('SAVED')
    bill['source_file'] = 'renamed.pdf'
    assert save_bill(bill, db).startswith('SKIPPED')
    bill['total_due'] = '999.00'
    with pytest.raises(ValueError, match='different details'):
        save_bill(bill, db)
    assert len(read_bills(db)) == 1


def test_payment_date_amount_and_reimport_preserved(tmp_path):
    bill = parse_pdf(ROOT / 'examples' / 'demo_water_bill_2026_04.pdf')
    db = tmp_path / 'water.sqlite'
    save_bill(bill, db)
    row = read_bills(db).iloc[0]
    assert row.payment_date is None
    record_payment(db, row.bill_id, '2026-05-02', '75.00')
    save_bill(bill, db)
    row = read_bills(db).iloc[0]
    assert row.payment_date == '2026-05-02'
    assert row.payment_amount == 75
    with pytest.raises(ValueError, match='different payment'):
        record_payment(db, row.bill_id, '2026-05-03', '75.00')


def test_migrate_original_water_schema(tmp_path):
    bill = parse_pdf(ROOT / 'examples' / 'demo_water_bill_2026_04.pdf')
    db = tmp_path / 'water.sqlite'
    save_bill(bill, db)
    with sqlite3.connect(db) as conn:
        conn.execute('ALTER TABLE water_bills DROP COLUMN payment_amount_cents')
    assert save_bill(bill, db).startswith('SKIPPED')
    assert len(read_bills(db)) == 1


def test_cash_and_receipts_are_not_added_twice(tmp_path):
    owner, _ = build_demo_databases(tmp_path / 'demo')
    water = build_demo_water_database(tmp_path / 'demo')
    report = monthly_water_report(water, owner)
    assert report.water_billed.sum() == 540
    assert report.water_paid.sum() == 540
    assert report.utility_reimbursements.sum() == 75  # Existing AppFolio receipt.
    assert report.unconfirmed_bills.sum() == 0
    # Confirmed May payment for an April bill belongs to May, not April.
    with sqlite3.connect(water) as conn:
        conn.execute("UPDATE water_bills SET payment_date='2026-05-02' WHERE bill_date='2026-04-17'")
    report = monthly_water_report(water, owner).set_index('month')
    assert report.loc['2026-04', 'water_paid'] == 0
    assert report.loc['2026-05', 'water_paid'] == 157.5


def test_public_app_includes_water_and_preserves_privacy(monkeypatch):
    monkeypatch.setenv('NESIAOS_WATER_DB_PATH', '/nonexistent/private.sqlite')
    app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=60).run()
    assert not app.exception
    titles = [h.value for h in app.subheader]
    assert 'Water Bills & Utility Reimbursements' in titles
    assert app.metric[0].value == '$922.75'  # September cash after $87.30 water.
    assert not app.button  # Public demo cannot edit payment records.
    app.query_params['page'] = 'privacy'
    app.run()
    assert not app.exception
    assert app.title[0].value == 'NesiaOS Privacy Policy'
