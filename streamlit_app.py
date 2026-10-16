"""Public Streamlit Cloud entrypoint using fictional NesiaOS statements only.

Run: streamlit run streamlit_app.py
The private deployment continues to use dashboard/app.py unchanged.
"""

from pathlib import Path
import os
import runpy
import sqlite3
import tempfile


ROOT = Path(__file__).resolve().parent


def build_demo_databases(destination: Path) -> tuple[Path, Path]:
    """Import exactly the approved example PDFs into new temporary SQLite files."""
    from src.services.appfolio_importer import HEADERS, parse_pdf as parse_owner
    from src.services.mortgage_importer import parse_pdf as parse_mortgage, save_to_sqlite

    destination = Path(destination)
    owner_db = destination / "nesiaos.sqlite"
    mortgage_db = destination / "mortgage.sqlite"
    if owner_db.exists() or mortgage_db.exists():
        raise FileExistsError("Demo import requires an empty destination")
    destination.mkdir(parents=True, exist_ok=True)

    rows = []
    for month in range(4, 10):
        pdf = ROOT / "examples" / f"demo_owner_statement_2026_{month:02d}.pdf"
        if not pdf.is_file():
            raise FileNotFoundError(f"Missing synthetic demo file: {pdf.name}")
        statement_rows, _totals = parse_owner(pdf)  # importer verifies balances
        rows.extend(statement_rows)

    # Same transaction schema as the normal AppFolio importer.
    numeric = {"income", "expense", "amount", "statement_balance"}
    definitions = ", ".join(
        f'"{key}" ' + ("REAL" if key in numeric else
                       "INTEGER" if key == "source_row" else "TEXT")
        for key in HEADERS
    )
    fields = ", ".join(f'"{key}"' for key in HEADERS)
    placeholders = ", ".join("?" for _ in HEADERS)
    with sqlite3.connect(owner_db) as conn:
        conn.execute(
            f"CREATE TABLE transactions ({definitions}, PRIMARY KEY (transaction_id))"
        )
        conn.executemany(
            f"INSERT INTO transactions ({fields}) VALUES ({placeholders})",
            [[row[key] for key in HEADERS] for row in rows],
        )

    mortgage_pdf = ROOT / "examples" / "demo_mortgage_payment_history_2026.pdf"
    if not mortgage_pdf.is_file():
        raise FileNotFoundError(f"Missing synthetic demo file: {mortgage_pdf.name}")
    events = parse_mortgage(mortgage_pdf)
    save_to_sqlite(events, mortgage_db)

    with sqlite3.connect(owner_db) as conn:
        owner_months = conn.execute(
            "SELECT COUNT(DISTINCT substr(statement_start, 1, 7)) FROM transactions"
        ).fetchone()[0]
    with sqlite3.connect(mortgage_db) as conn:
        payment_count = conn.execute(
            "SELECT COUNT(*) FROM mortgage_events WHERE event_type = 'mortgage_payment'"
        ).fetchone()[0]
    if owner_months != 6 or payment_count != 6:
        raise ValueError("Incomplete synthetic demo; refusing to display dashboard")
    return owner_db, mortgage_db


def main() -> None:
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def prepare_demo() -> tuple[Path, Path]:
        return build_demo_databases(Path(tempfile.mkdtemp(prefix="nesiaos_public_demo_")))

    owner_db, mortgage_db = prepare_demo()
    # Override preexisting settings: this entrypoint must NEVER use private data.
    os.environ["NESIAOS_DB_PATH"] = str(owner_db)
    os.environ["NESIAOS_MORTGAGE_DB_PATH"] = str(mortgage_db)
    os.environ["NESIAOS_PUBLIC_DEMO"] = "1"
    runpy.run_path(str(ROOT / "dashboard" / "app.py"), run_name="__main__")


if __name__ == "__main__":
    main()
