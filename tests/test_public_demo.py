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
