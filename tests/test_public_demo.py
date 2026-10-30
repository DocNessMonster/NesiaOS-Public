"""The public Streamlit entrypoint must operate on fictional data only."""

import sqlite3

import pytest

from streamlit_app import build_demo_databases
from src.services.financial_report import monthly_report


def test_public_demo_bootstraps_both_synthetic_data_sources(tmp_path):
    owner_db, mortgage_db = build_demo_databases(tmp_path / "synthetic")

    report = monthly_report(owner_db)
    assert len(report) == 6
    assert report["month"].tolist() == [f"2026-{month:02d}" for month in range(4, 10)]

    with sqlite3.connect(mortgage_db) as conn:
        payment_count, total_mortgage = conn.execute(
            "SELECT COUNT(*), SUM(payment_amount) FROM mortgage_events "
            "WHERE event_type = 'mortgage_payment'"
        ).fetchone()
        escrow_count = conn.execute(
            "SELECT COUNT(*) FROM mortgage_events "
            "WHERE event_type = 'escrow_disbursement'"
        ).fetchone()[0]
    assert payment_count == 6
    assert escrow_count == 2
    assert round(float(report["owner_distributions"].sum()) - total_mortgage, 2) == 4475.30


def test_public_demo_never_writes_into_an_existing_database(tmp_path):
    destination = tmp_path / "synthetic"
    destination.mkdir()
    (destination / "nesiaos.sqlite").write_bytes(b"existing data must not be overwritten")
    with pytest.raises(FileExistsError):
        build_demo_databases(destination)


def test_monthly_table_formats_currency_without_changing_numeric_values(monkeypatch):
    from pathlib import Path

    import pandas as pd
    from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
    from streamlit.testing.v1 import AppTest
    from src.services import financial_report

    original_report = financial_report.monthly_report

    def report_with_formatting_edge_cases(*args, **kwargs):
        report = original_report(*args, **kwargs).copy()
        report["operating_income"] = 1234.5
        report["operating_expenses"] = 0.1 + 0.2
        report["owner_distributions"] = -12.5
        return report

    monkeypatch.setattr(financial_report, "monthly_report", report_with_formatting_edge_cases)
    # The public entrypoint overrides all database paths with synthetic fixtures.
    for key in ("NESIAOS_DB_PATH", "NESIAOS_MORTGAGE_DB_PATH",
                "NESIAOS_WATER_DB_PATH", "NESIAOS_PUBLIC_DEMO"):
        monkeypatch.setenv(key, "")
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "streamlit_app.py"),
        default_timeout=30,
    ).run()
    assert not app.exception
    table = app.dataframe[-1]
    # Streamlit moved Arrow data into a nested message in newer releases.
    arrow = getattr(table.proto, "arrow_data", table.proto)
    assert arrow.styler.display_values, "Monthly currency formatting is missing"
    displayed = convert_arrow_bytes_to_pandas_df(arrow.styler.display_values)
    assert displayed.iloc[0]["Operating income (incl. reimbursements)"] == "$1,234.50"
    assert displayed.iloc[0]["Operating expenses"] == "$0.30"
    assert displayed.iloc[0]["Owner distributions"] == "-$12.50"
    assert displayed.iloc[0]["Month"] == "2026-04"
    assert table.value.iloc[0]["Operating expenses"] == 0.1 + 0.2
    assert all(pd.api.types.is_numeric_dtype(table.value[column])
               for column in table.value.columns if column != "Month")
