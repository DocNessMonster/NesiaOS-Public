import sqlite3

import pandas as pd
import pytest

from src.services.property_value_report import read_valuations, calculate_equity, equity_history
from streamlit_app import build_demo_valuation_database


def test_missing_valuation_database_is_not_created(tmp_path):
    db = tmp_path / "absent.sqlite"
    assert read_valuations(db).empty
    assert not db.exists()


def test_demo_values_are_fictional_and_keep_six_months(tmp_path):
    db = build_demo_valuation_database(tmp_path)
    valuations = read_valuations(db)
    assert len(valuations) == 6
    assert valuations.iloc[-1]["estimated_value"] == 282500
    assert set(valuations["provider"]) == {"Synthetic demo"}
    assert valuations.iloc[-1]["range_low"] == 257500
    with pytest.raises(FileExistsError):
        build_demo_valuation_database(tmp_path)


def test_equity_can_be_negative_and_is_exact_to_cents():
    assert calculate_equity(200000, 250000) == (-50000, -25)
    assert calculate_equity("250000.10", "100000.05")[0] == 150000.05


@pytest.mark.parametrize("value,balance", [(0, 1), (100, -1), ("NaN", 10), (100, "Infinity"), (100, None)])
def test_invalid_equity_inputs_are_rejected(value, balance):
    with pytest.raises(ValueError):
        calculate_equity(value, balance)


def test_history_does_not_use_future_mortgage_balances(tmp_path):
    valuations = read_valuations(build_demo_valuation_database(tmp_path))
    payments = pd.DataFrame({
        "effective_date": ["2026-05-01", "2026-09-01", "2026-10-01"],
        "principal_balance": [200000, 190000, 180000],
    })
    history = equity_history(valuations, payments)
    assert pd.isna(history.iloc[0]["estimated_equity"])
    assert history.iloc[1]["estimated_equity"] == 76500
    assert history.iloc[-1]["estimated_equity"] == 92500


def test_multiple_properties_are_not_silently_combined(tmp_path):
    db = build_demo_valuation_database(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE property_valuations SET property_key = 'other-property' WHERE retrieval_month = '2026-04'")
    with pytest.raises(ValueError, match="Multiple properties"):
        read_valuations(db)
