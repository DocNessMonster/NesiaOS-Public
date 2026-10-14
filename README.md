# NesiaOS

**A self-hosted rental-property financial analytics dashboard, built with Python, SQLite, and Streamlit.**

NesiaOS turns text-based AppFolio owner statements into structured transactions and monthly financial reporting. It demonstrates a practical workflow from PDF ingestion through validation, storage, and interactive visualization.

> **Current scope:** Owner-statement operating activity only. Mortgage payments, owner-paid costs, and full property profit calculations are not yet incorporated.

## What works in V1

- Extract transactions from supported text-based AppFolio PDF owner statements.
- Reconcile extracted transactions against statement totals and running cash balances.
- Categorize income, operating expenses, and owner distributions (transfers).
- Write normalized transactions to CSV and SQLite with duplicate-import protection.
- Calculate monthly operating income, expenses, distributions, and operating cash flow.
- Display metrics, charts, and a monthly summary in a Streamlit dashboard.
- Run automated tests against a **fully fictional** example statement.

## Architecture

```text
AppFolio owner statement (PDF)
           |
           v
src/services/appfolio_importer.py
   |                  |
   v                  v
  CSV                SQLite
                        |
                        v
             financial_report.py
                        |
                        v
                 dashboard/app.py
                   Streamlit
```

## Quick start (synthetic data only)

Requires Python 3.12 or newer. From the repository root:

```bash
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: ` .venv\Scripts\Activate.ps1 `
- Linux/macOS: `source .venv/bin/activate`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Import the committed **synthetic** sample statement:

```bash
python -m src.services.appfolio_importer examples/sample_owner_statement.pdf --out-dir demo_data
```

Run the tests:

```bash
python -m pytest -q
```

Run the dashboard using the generated *fictional* database. Set the environment variable in the **same terminal** before launching Streamlit.

Linux/macOS:

```bash
export NESIAOS_DB_PATH=demo_data/nesiaos.sqlite
python -m streamlit run dashboard/app.py
```

Windows PowerShell:

```powershell
$env:NESIAOS_DB_PATH = "demo_data/nesiaos.sqlite"
python -m streamlit run dashboard/app.py
```

The app will display the fictional sample's finances, not the developer's private data.

## Using your own statements

Supply an AppFolio text-based owner statement to the importer, choose an output directory, and point `NESIAOS_DB_PATH` at the resulting SQLite database. **Never commit personal statements, exported transactions, databases, credentials, or identifiable screenshots.**

The default database location is `local_data/production_verified/nesiaos.sqlite` for the private deployment. This path is ignored by Git.

The importer currently expects a particular owner-statement table layout and is not a universal PDF extraction system. Review any unknown categories before trusting a financial report.

## Financial definitions

- **Operating income:** statement transactions classified as income.
- **Operating expenses:** statement transactions classified as operating expenses.
- **Owner distributions:** transfers to the owner, shown separately; not additional expenses.
- **Operating cash flow:** operating income less operating expenses, **before mortgage and costs paid outside the property manager**.

These figures are not a complete tax, accounting, or investment-performance report.

## Tests

Tests cover statement extraction, totals reconciliation, classification, and owner-distribution handling. Additional integration and edge-case coverage is planned.

## Roadmap

- Mortgage and owner-paid expense integration.
- Additional financial data sources.
- More robust categorization and reporting validation.
- Automated document ingestion and scheduled updates.
- Expanded multi-property reporting.

## Broader vision

NesiaOS began as a concept for an AI-powered attention manager that highlights meaningful changes across connected data sources. The rental-finance dashboard is the first implemented module; intelligent alerts and cross-domain integrations remain future work.

## Security and privacy

The public example is fictional. Actual statements, database contents, and private deployment configuration do not belong in the public repository. The self-hosted deployment is accessed through private Tailscale networking; this repository does **not** provide a public live demo.
