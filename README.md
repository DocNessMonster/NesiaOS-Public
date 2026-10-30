# NesiaOS

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nesiaos-public.streamlit.app/)

**[Try the live, interactive NesiaOS demo](https://nesiaos-public.streamlit.app/)** — explore the unified rental and mortgage dashboard with **100% fictional financial data**. No personal financial records are included.

**A self-hosted rental-property financial analytics dashboard built with Python, SQLite, and Streamlit.**

NesiaOS converts supported property-management and mortgage-history PDFs into validated, structured data and combines them in a single interactive rental-property dashboard. This public repository contains only application code, automated tests, and **completely fictional demonstration documents**. It never includes the owner's real financial information. A separate public Streamlit Cloud demo runs only on fictional sample data.

## Water bills in V1.2

The dashboard includes six fictional April–September utility bills, totaling **$540.00**,
with invented confirmed payments. Combined six-month owner cash flow after mortgage
and water payments is **$3,935.30**. The existing **$75.00** utility reimbursement is
read from AppFolio and is not added to income a second time.

The water section shows current service charges, carried balances, adjustments,
total due, receipts, and confirmed payments separately. A monthly charge/receipt
difference does not automatically establish a tenant balance: reimbursements may lag.
Real bills without confirmed payment dates and amounts stay out of cash flow. In the
private dashboard, use **Confirm a water bill payment** after checking the actual
payment. Partial or combined payments require review rather than guessing.

`NESIAOS_WATER_DB_PATH` selects a water database; the private default is
`local_data/water/water.sqlite`. The public entrypoint always overrides this setting
with a newly built synthetic database and never connects to Gmail.

Generate only the fictional water PDFs with `python examples/generate_water_demo.py`
(requires reportlab). The July fixture intentionally continues on a second page.
Expected utility totals are in `examples/demo_water_expected_totals.csv`.
The original `demo_expected_totals.csv` still documents the pre-water baseline.

For local Gmail automation, install `python -m pip install -r requirements-gmail.txt`.
Keep OAuth credentials and tokens in ignored `local_data/gmail/`. Optional
`NESIAOS_WATER_ACCOUNT` restricts imports to one utility account;
`NESIAOS_WATER_QUERY` overrides the received-bill search. The importer includes
archived received bills and excludes Sent mail. Scheduling on one computer updates
that computer's database; another server needs its own import or a private DB sync.

## What's new in V1.1

- Import and reconcile supported AppFolio-style owner statements and rotated mortgage payment-history PDFs.
- Persist mortgage payments and escrow disbursements in a separate SQLite database; repeated imports do not double-count transactions.
- Show **monthly** and **year-to-date** rental income, operating expenses, owner cash flow, mortgage payments, principal and interest.
- Visualize actual cash flow by month and a color-coded stacked breakdown of operating expenses, principal, interest, and escrow contributions.
- Display latest principal balance and taxes/insurance paid from escrow without double-counting them in cash flow.
- Use six synthetic monthly owner statements and a synthetic mortgage history to exercise an example negative cash-flow month.

**Actual cash flow** here means *AppFolio owner distributions minus mortgage payments paid personally*. Confirmed water payments are now also subtracted; other owner-paid costs are not included. Owner distributions are transfers, not operating expenses; principal reduces debt rather than constituting an operating expense. The dashboard includes only months for which **both data sources** are available.

## Architecture

```text
Property-manager PDF ---> appfolio_importer.py ---> owner.sqlite ---+
                                                                  |
Mortgage history PDF ---> mortgage_importer.py --> mortgage.sqlite-+--> dashboard/app.py
                                                                          Streamlit
```

## Interactive public demo on Streamlit Community Cloud

**Live URL: https://nesiaos-public.streamlit.app/**

The public demo has its own entrypoint, `streamlit_app.py`, which automatically imports only the committed **fictional** PDF fixtures into fresh temporary SQLite databases. It does not use the private Ubuntu server, a real owner's statements, or private databases. The dashboard displays a prominent public-demo label.

To deploy: sign in to [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app / Deploy app**, connect the public GitHub repository `DocNessMonster/NesiaOS-Public`, set branch `main` and entrypoint `streamlit_app.py`, choose a public app URL, and deploy. Streamlit installs dependencies from `requirements.txt`.

To launch the same public demo locally, run `python -m streamlit run streamlit_app.py` (no environment variables or manual importing needed).

## Run the fully fictional public demo

Requires Python 3.12+ and the dependencies in `requirements.txt`. Run the following from the repository root:

```bash
python -m pip install -r requirements.txt
```

Import the six **synthetic** owner statements into one new database:

**Windows PowerShell:**

```powershell
Get-ChildItem examples/demo_owner_statement_2026_*.pdf | ForEach-Object {
    python -m src.services.appfolio_importer $_.FullName --out-dir local_data/demo_public/imported
}
python -m src.services.mortgage_importer examples/demo_mortgage_payment_history_2026.pdf --db local_data/demo_public/imported/mortgage.sqlite
$env:NESIAOS_DB_PATH = (Resolve-Path local_data/demo_public/imported/nesiaos.sqlite).Path
$env:NESIAOS_MORTGAGE_DB_PATH = (Resolve-Path local_data/demo_public/imported/mortgage.sqlite).Path
python -m streamlit run dashboard/app.py
```

**Linux/macOS:**

```bash
mkdir -p local_data/demo_public/imported
for pdf in examples/demo_owner_statement_2026_*.pdf; do
    python -m src.services.appfolio_importer "$pdf" --out-dir local_data/demo_public/imported
done
python -m src.services.mortgage_importer examples/demo_mortgage_payment_history_2026.pdf --db local_data/demo_public/imported/mortgage.sqlite
export NESIAOS_DB_PATH="$PWD/local_data/demo_public/imported/nesiaos.sqlite"
export NESIAOS_MORTGAGE_DB_PATH="$PWD/local_data/demo_public/imported/mortgage.sqlite"
python -m streamlit run dashboard/app.py
```

The dashboard opens locally in your browser. Expect **April–September 2026**, a July negative cash-flow month, and a six-month pre-water baseline of **$4,475.30**, or **$3,935.30** after confirmed water payments. See [`examples/demo_expected_totals.csv`](examples/demo_expected_totals.csv) for reference values. Both demo databases are created under ignored `local_data/`; no real financial data is required.

Run automated tests:

```bash
python -m pytest -q
```

## Demo fixture generation

The PDFs in [`examples/`](examples/) were **generated from scratch** and visibly marked as synthetic. They are not actual documents issued by AppFolio or any lender, and they contain no real owner's loan number, banking details, property address, or transaction history. To regenerate the files (optional):

```bash
python -m pip install reportlab
python examples/generate_demo_pdfs.py
```

Rebuilding the PDFs may change their byte-level checksums. The publishing workflow checks the approved fixture hashes in `examples/SYNTHETIC_SHA256.txt`; update and review that file only after validating replacements.

## Scope and security

- Supported PDF table **layouts** only; not a general-purpose parser for every property manager or lender.
- Imported PDFs, personal exports, database files, `.env` files, and deployment configuration must remain **local and untracked**.
- The public release is built from a **strict allowlist** and excludes private repository history. An additional fixture-hash check guards against accidentally publishing other PDFs in place of the approved samples.
- `NESIAOS_DB_PATH` selects the property-management SQLite file. `NESIAOS_MORTGAGE_DB_PATH` selects the mortgage SQLite file; otherwise the private local default is `local_data/mortgage/mortgage.sqlite`.
- Do not use the synthetic example figures for financial decisions. These metrics are operational reporting, not tax or investment advice.

## Roadmap

- Optional property-equity estimates.
- Additional import formats and classification tests.
- More flexible reporting for multiple properties.

NesiaOS began as a broader vision for AI-assisted personal operations; the rental-property analytics system is its first deployed module.

