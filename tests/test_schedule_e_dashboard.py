"""Synthetic tests for CSV export and public-demo capital isolation."""
import csv
import io

from src.services.capital_report import list_improvements
from src.services.schedule_e_export import schedule_e_csv
from streamlit_app import build_demo_capital_database


def test_schedule_e_csv_marks_incomplete_and_preserves_assets():
    report = {
        "year": 2026,
        "lines": {3: 1200.0, 17: 100.0},
        "labels": {3: "Rents received", 17: "Utilities"},
        "income": 1200.0,
        "known_expenses_excluding_depreciation": 100.0,
        "provisional_difference": 1100.0,
        "capital_spending": 6250.0,
        "capital_improvements": [
            {"description": "Fictional upgrade",
             "completion_date": "2026-07-10",
             "placed_in_service_date": "2026-07-10",
             "cost_cents": 625000},
        ],
        "review": ["Depreciation not calculated"],
    }
    payload = schedule_e_csv(report)
    rows = list(csv.reader(io.StringIO(payload.decode("utf-8-sig"))))
    assert ["STATUS", "NOT FILING READY"] in rows
    assert ["17", "Utilities", "100.00"] in rows
    assert ["Fictional upgrade", "2026-07-10", "2026-07-10", "6250.00"] in rows
    assert ["Depreciation not calculated"] in rows
    assert b"NOT taxable income" in payload


def test_public_demo_capital_assets_are_fictional_and_isolated(tmp_path):
    db = build_demo_capital_database(tmp_path)
    records = list_improvements(db)
    assert len(records) == 1
    assert records[0]["description"] == "Fictional rental kitchen upgrade"
    assert records[0]["cost_cents"] == 625000
    assert records[0]["placed_in_service_date"] == "2026-07-10"
