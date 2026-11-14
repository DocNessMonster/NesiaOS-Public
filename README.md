# NesiaOS

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nesiaos-public.streamlit.app/)

**[Try the live, interactive NesiaOS demo](https://nesiaos-public.streamlit.app/)** — explore the unified rental and mortgage dashboard with **100% fictional financial data**. No personal financial records are included.

**A self-hosted rental-property financial analytics dashboard built with Python, SQLite, and Streamlit.**

NesiaOS converts supported property-management and mortgage-history PDFs into validated, structured data and combines them in a single interactive rental-property dashboard. This public repository contains only application code, automated tests, and **completely fictional demonstration documents**. It never includes the owner's real financial information. A separate public Streamlit Cloud demo runs only on fictional sample data.

## NesiaOS v1.3 — Schedule E & Depreciation Explorer (November 2026)

**Live demo:** https://nesiaos-public.streamlit.app/

V1.3 adds a preliminary Schedule E tax-reporting section **at the bottom of the
rental dashboard**, and a separate interactive depreciation/reconciliation
explorer using **entirely fictional information**.

- Preliminary **Schedule E**: reconcile fictional rental income and expenses
  into IRS-like categories (management, maintenance, repairs, commissions,
  mortgage interest, insurance, property taxes, utilities); display the annual
  totals, capital spending, review flags, and a downloadable **NOT FILING READY**
  CSV. Capital improvements are tracked separately from current expenses.
- **Depreciation scenario calculator**: vary the *fictional* purchase price,
  eligible purchase closing costs, land/building split, pre-rental renovations,
  estimated FMV at conversion, rental availability date, and a later qualifying
  building improvement. It shows provisional 2025 and 2026 straight-line
  27.5-year, mid-month estimates and an illustrative prior-year difference.
- **Water reconciliation:** support confirmed multi-bill bank payment
  allocations and avoid counting a water withdrawal twice. This is part of the
  underlying reporting logic; the live example uses invented payments.
- **Historical asset handling:** the synthetic demo contains a fictional
  capital improvement; no actual property, loan, tenant, tax return, or tax
  documents are published.
- **Tax caution:** no tax filing or 1040-X amendment is generated. Depreciation
  is shown in the separate educational scenario calculator, **not automatically
  posted to Schedule E Line 18**. The preliminary Schedule E worksheet continues
  to flag unverified basis, year coverage, and expense classifications.

### Where to find the new features

Open the [public demo](https://nesiaos-public.streamlit.app/), scroll past
**Monthly Financial Details** to **Schedule E / Tax Reporting**, then continue to
**Depreciation & Prior-Year Reconciliation — Demo**.

To run the **complete synthetic demo locally**, from the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
python -m pytest -q
```

The public demo boots temporary SQLite databases from approved **fictional**
fixtures. It makes no Gmail, mortgage-lender, AppFolio, bank, or valuation
API requests; production imports and any future client-account automation
remain outside this release.

## Feature overview

- Import supported property-management and mortgage-history PDFs into SQLite
  for reconciled rental-property reporting.
- Explore monthly and year-to-date income, expenses, mortgage payments,
  principal, interest, escrow activity, and owner cash flow.
- Track water charges separately from confirmed payments and utility
  reimbursements to avoid double-counting.
- Review estimated property equity alongside dated valuation and equity
  history, with source details, estimate ranges, and mortgage balance dates.
- Read financial tables with consistent dollar formatting while retaining
  numeric values for sorting and calculations.
- Explore preliminary Schedule E categories, fictional capital improvements,
  and an interactive **fictional 2025–2026 depreciation scenario**.
- Explore the public Streamlit demo using completely fictional financial
  documents and valuation snapshots.

## Previous updates — October 30, 2026

### Estimated property equity and history

The public demo now includes six fictional April–September 2026 valuation
snapshots. The equity section displays the latest estimated home value,
source and retrieval date, estimate range, latest mortgage principal balance
and its date, and estimated equity in dollars and as a percentage of value.
A chart and expandable table show valuation and equity history.

The latest-equity summary uses the latest saved valuation and mortgage
balance independently of the reporting-month filter. Historical equity pairs
each valuation with the latest mortgage record dated on or before its
retrieval date; equity remains blank when no earlier balance is available.

Estimated equity equals estimated home value minus mortgage principal.
It is separate from rental cash flow and excludes selling costs, taxes,
and other loans. An automated estimate is not an appraisal.

The public demo generates all valuation snapshots locally, makes no
valuation API calls, and overrides the valuation database path with a
fresh synthetic database.

### Consistent currency formatting

Monthly Financial Details now displays every monetary column with dollar
signs, thousands separators, and two decimal places, using the same
negative-dollar convention as the summary metrics (for example, -$12.50).
Underlying values remain numeric for sorting and calculations. Utility-table
amounts also use currency formatting, and displayed cash flow is rounded
to cents.

### Water bill reporting — V1.2

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

For local Gmail automation in the private checkout, install `python -m pip install -r requirements-gmail.txt`.
Keep OAuth credentials and tokens in ignored `local_data/gmail/`. Optional
`NESIAOS_WATER_ACCOUNT` restricts imports to one utility account;
`NESIAOS_WATER_QUERY` overrides the received-bill search. The importer includes
archived received bills and excludes Sent mail. Scheduling on one computer updates
that computer's database; another server needs its own import or a private DB sync.

## Earlier updates — V1.1

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

The public demo has its own entrypoint, `streamlit_app.py`, which imports the
committed **fictional** PDF fixtures and generates six fictional valuation
snapshots and a fictional capital asset in fresh temporary SQLite databases. It does not use the private Ubuntu server, a real owner's statements, or private databases. The dashboard displays a prominent public-demo label.

To deploy: sign in to [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app / Deploy app**, connect the public GitHub repository `DocNessMonster/NesiaOS-Public`, set branch `main` and entrypoint `streamlit_app.py`, choose a public app URL, and deploy. Streamlit installs dependencies from `requirements.txt`.

To launch the same public demo locally, run `python -m streamlit run streamlit_app.py` (no environment variables or manual importing needed).

## Run the fully fictional public demo

Requires Python 3.12+ and the dependencies in `requirements.txt`. Run the following from the repository root:

```bash
python -m pip install -r requirements.txt
```

For the complete public demo—including water payments and valuation/equity
history—use `python -m streamlit run streamlit_app.py`. The manual steps below
initialize the owner-statement and mortgage databases only.

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
- `NESIAOS_VALUATION_DB_PATH` selects the saved valuation SQLite file;
  otherwise the private local default is
  `local_data/valuation/valuations.sqlite`. The public demo overrides this
  setting with its synthetic database.
- Do not use the synthetic example figures for financial decisions. These metrics are operational reporting, not tax or investment advice.

## Roadmap

- Verified private asset/basis register and full multi-year MACRS schedule.
- 2025 source-by-source Schedule E audit and amendment-review workflow.
- Optional AppFolio and mortgage email automation, pending safe import validation.
- Additional import formats and classification tests.
- More flexible reporting for multiple properties.

NesiaOS began as a broader vision for AI-assisted personal operations; the rental-property analytics system is its first deployed module.

