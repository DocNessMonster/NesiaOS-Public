"""NesiaOS MVP: import text-based AppFolio owner statements to CSV and SQLite.
Usage: python nesiaos_import_appfolio.py 'statement.pdf' --out-dir ./nesiaos_data
Requires: pip install pdfplumber
"""
import argparse
import csv
import hashlib
import re
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

HEADERS = ['transaction_id','property','statement_start','statement_end','date','payee_payer','payment_type','reference','description','category','flow_type','income','expense','amount','statement_balance','source_file','source_row']

def money(value):
    return Decimal(str(value or '0').replace(',','').replace('$','').strip() or '0')


def category(desc, income=0):
    """Classify property management transactions by description."""

    s = desc.lower().strip()

    # Owner transfers (not operating expenses)
    if s.startswith("owner draws"):
        return "owner_distribution", "transfer"

    # Income
    if s.startswith("rent income"):
        return "rent_income", "income"

    if s.startswith("utilities reimbursement"):
        return "utility_reimbursement", "income"

    # Property management and leasing
    if s.startswith("management fees"):
        return "management_fee", "operating_expense"

    if s.startswith("renewal fee"):
        return "leasing_fee", "operating_expense"

    # Maintenance and repairs
    if s.startswith("landscaping yard care"):
        if float(income) > 0:
            return "landscaping_reimbursement", "income"
        return "landscaping", "operating_expense"

    if s.startswith("plumbing maintenance"):
        return "plumbing", "operating_expense"

    if s.startswith("hvac maintenance"):
        return "hvac", "operating_expense"

    if s.startswith("electrical maintenance"):
        return "electrical", "operating_expense"

    if s.startswith("smoke alarm"):
        return "safety_equipment", "operating_expense"

    # Taxes
    if s.startswith("tax - sales"):
        return "sales_tax", "operating_expense"

    # Flag anything unfamiliar for review
    return "uncategorized", "unknown"


def parse_pdf(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        text='\n'.join(page.extract_text() or '' for page in pdf.pages)
        match=re.search(r'Period:\s*(\d{2}\s+\w+\s+\d{4})\s*-\s*(\d{2}\s+\w+\s+\d{4})',text)
        if not match: raise ValueError('Statement period not found')
        start,end=[datetime.strptime(m,'%d %b %Y').date().isoformat() for m in match.groups()]
        # Property identification will be configurable.
        # Leave blank until the extraction method is generalized.
        property_name = ""  # unknown properties remain blank for review
        tables=[t for p in pdf.pages for t in p.extract_tables()]
        main=next((t for t in tables if t and t[0] and t[0][0]=='Date' and 'Description' in t[0]),None)
        if not main: raise ValueError('Transaction table not found')
        rows=[]; opening=closing=None; expected_income=expected_expense=None
        for idx, row in enumerate(main[1:],start=1):
            if not row: continue
            cells=[(v or '').replace('\n',' ').strip() for v in row]
            if 'Beginning Cash Balance' in cells[4]: opening=money(cells[7]);continue
            if 'Ending Cash Balance' in cells[4]: closing=money(cells[7]);continue
            if cells[0].startswith('Total '):
                mm=re.findall(r'[\d,]+\.\d{2}',cells[0]);
                if len(mm)>=2:expected_income,expected_expense=map(money,mm[-2:])
                continue
            if not re.fullmatch(r'\d{2}/\d{2}/\d{4}',cells[0]):continue
            date=datetime.strptime(cells[0],'%m/%d/%Y').date().isoformat()
            income,expense,balance=money(cells[5]),money(cells[6]),money(cells[7])
            if income and expense: raise ValueError(f'Both income and expense on row {idx}')
            cat, flow = category(cells[4], income=money(cells[5]))
            if cat=='landscaping':
                cat,flow=('landscaping_reimbursement','income') if income else ('landscaping','operating_expense')
            stable='|'.join([hashlib.sha256(path.read_bytes()).hexdigest(),str(idx),date,cells[4],str(income),str(expense)])
            rows.append(dict(transaction_id=hashlib.sha256(stable.encode()).hexdigest()[:24],property=property_name,statement_start=start,statement_end=end,date=date,payee_payer=cells[1],payment_type=cells[2],reference=cells[3],description=cells[4],category=cat,flow_type=flow,income=f'{income:.2f}',expense=f'{expense:.2f}',amount=f'{income-expense:.2f}',statement_balance=f'{balance:.2f}',source_file=path.name,source_row=idx))
        if opening is None or closing is None or expected_income is None: raise ValueError('Missing statement reconciliation fields')
        observed_income=sum((money(r['income']) for r in rows),Decimal(0))
        observed_expense=sum((money(r['expense']) for r in rows),Decimal(0))
        if (observed_income,observed_expense,opening+observed_income-observed_expense)!=(expected_income,expected_expense,closing):
            raise ValueError(f'Reconciliation failed: extracted {observed_income}/{observed_expense}; expected {expected_income}/{expected_expense}')
        running=opening
        for row in rows:
            running+=money(row['amount'])
            if running!=money(row['statement_balance']):raise ValueError(f'Balance mismatch at {row["date"]}: {running} != {row["statement_balance"]}')
        return rows, dict(opening=opening,closing=closing,income=observed_income,expense=observed_expense)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('pdf',type=Path)
    ap.add_argument('--out-dir',type=Path,default=Path('nesiaos_data'))
    args=ap.parse_args();args.out_dir.mkdir(parents=True,exist_ok=True)
    rows,totals=parse_pdf(args.pdf)
    csv_file=args.out_dir/(args.pdf.stem+'_transactions.csv')
    with csv_file.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=HEADERS);writer.writeheader();writer.writerows(rows)
    db=args.out_dir/'nesiaos.sqlite'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS transactions ('+', '.join(f'"{h}" '+('REAL' if h in ('income','expense','amount','statement_balance') else 'INTEGER' if h=='source_row' else 'TEXT') for h in HEADERS)+', PRIMARY KEY (transaction_id))')
        sql='INSERT INTO transactions ('+','.join('"'+h+'"' for h in HEADERS)+') VALUES ('+','.join('?' for _ in HEADERS)+') ON CONFLICT(transaction_id) DO UPDATE SET category=excluded.category, flow_type=excluded.flow_type'
        conn.executemany(sql,([r[h] for h in HEADERS] for r in rows))
        conn.commit()
    print(f'PASS: {len(rows)} transactions; income {totals["income"]}; expense {totals["expense"]}; ending balance {totals["closing"]}')
    print(csv_file);print(db)
if __name__=='__main__': main()
