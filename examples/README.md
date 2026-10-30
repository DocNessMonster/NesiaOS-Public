# NesiaOS V1.1 - Synthetic Public Demo Data

**Every name, amount, date-specific transaction, reference, loan balance, and event here is fictional.** All PDFs are generated from scratch using `generate_demo_pdfs.py`; no real statement was copied, anonymized, edited, or embedded. These are compatibility-test fixtures, **not statements issued by AppFolio, a mortgage lender, or any other institution**.

## Contents

- `demo_owner_statement_2026_04.pdf` through `demo_owner_statement_2026_09.pdf` - six fictional monthly property management owner statements.
- `demo_mortgage_payment_history_2026.pdf` - rotated-table mortgage history containing six synthetic payments and two fictional escrow disbursements (property tax and insurance).
- `demo_expected_totals.csv` - exact expected dashboard values for April-September 2026.
- `generate_demo_pdfs.py` - reproducible generator written using ReportLab (`pip install reportlab` if regeneration is desired).

The files use the structural table conventions expected by NesiaOS' current PDF importers. The mortgage history deliberately uses vertically oriented rows to exercise the rotated-table parsing logic. These are **test fixtures**, not a claim that NesiaOS can parse every possible AppFolio or lender PDF.

## Verified demo scenario

- AppFolio-style statements: each month independently reconciles its income, expenses, running balance, and starting/ending cash balances.
- Mortgage: each payment reconciles principal + interest + escrow to the total; escrow disbursements are separate events.
- Importing the same mortgage PDF twice creates **no duplicate** records.
- The fictional data has a large repair in July, producing a negative actual cash flow in that month, making the bar chart more informative.
- Across April-September 2026, expected actual cash flow is **$4,475.30** (owner distributions minus mortgage payments). See the CSV for each month's amounts.

## Publishing safely

1. Keep **all genuine statements, exports, SQLite files, addresses, account numbers, API tokens, and personal details** in ignored local folders; never commit them to either GitHub repository.
2. Place only the fictional files in your public repository's `examples/` directory. The generator itself is also safe to publish.
3. Review your proposed public release file list, diff, archive, and GitHub Actions publication allowlist before pushing. A `.gitignore` protects only untracked files; it does **not** remove content already committed or prevent explicit publishing scripts from copying unexpected files.
4. Confirm `local_data/`, actual PDF filenames, `.sqlite` / `.db` files, and any secrets are excluded from the public release. Do not commit or upload private financial databases as test artifacts.
5. To see the demo in Streamlit, import these PDFs to a **fresh throwaway local demo database** in a clean checkout. Do not point demo imports at an existing personal financial database. The current dashboard expects a mortgage SQLite database under `local_data/mortgage/` and supports `NESIAOS_DB_PATH` for the property-management database.
6. Generate a public release only **after** reviewing the full public file list and confirming it contains synthetic assets only.

All amounts in this package are made up for demonstration. Actual property profits, tax treatment, and loan balances are not represented.


## Synthetic utility bills

`demo_water_bill_2026_04.pdf` through `demo_water_bill_2026_09.pdf` are six
entirely invented bills with fictional account `0000002026`, totaling $540.00.
They are visibly marked SYNTHETIC DEMO and are not redacted real statements.
July exercises a continuation page. `demo_water_expected_totals.csv` lists
charges, invented confirmed payments, and the existing AppFolio utility receipt.
Regenerate with `python examples/generate_water_demo.py` (reportlab required).
