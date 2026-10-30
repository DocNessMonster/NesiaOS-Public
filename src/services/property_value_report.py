"""Read dated valuations and calculate equity separately from rental cash flow."""

import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd


def read_valuations(db_path):
    """Read only; a missing database must not be created by the dashboard."""
    if not Path(db_path).is_file():
        return pd.DataFrame()
    with sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True) as conn:
        frame = pd.read_sql_query(
            "SELECT property_key, provider, retrieved_at, price_cents, low_cents, high_cents "
            "FROM property_valuations ORDER BY retrieved_at", conn,
        )
    if frame.empty:
        return frame
    if frame["property_key"].nunique() != 1:
        raise ValueError("Multiple properties found; select a single-property valuation database")
    frame["retrieved_at"] = pd.to_datetime(frame["retrieved_at"], utc=True, errors="raise")
    frame["price_cents"] = pd.to_numeric(frame["price_cents"], errors="raise")
    if frame["retrieved_at"].isna().any() or frame["price_cents"].isna().any() or (frame["price_cents"] <= 0).any():
        raise ValueError("Invalid valuation date or amount")
    for source, target in (("price_cents", "estimated_value"), ("low_cents", "range_low"),
                           ("high_cents", "range_high")):
        frame[target] = pd.to_numeric(frame[source], errors="raise") / 100
    return frame.sort_values("retrieved_at").reset_index(drop=True)


def calculate_equity(value, mortgage_balance):
    try:
        value, balance = Decimal(str(value)), Decimal(str(mortgage_balance))
    except InvalidOperation:
        raise ValueError("Missing or invalid valuation or mortgage balance") from None
    if not value.is_finite() or value <= 0 or not balance.is_finite() or balance < 0:
        raise ValueError("Equity needs a positive valuation and a nonnegative mortgage balance")
    return float(value - balance), float((value - balance) / value * 100)


def equity_history(valuations, payments):
    """Pair each estimate with the latest mortgage payment known by that date."""
    history = valuations[["retrieved_at", "provider", "estimated_value", "range_low", "range_high"]].copy()
    history = history.rename(columns={"retrieved_at": "valuation_date"})
    mortgage = payments[["effective_date", "principal_balance"]].copy()
    mortgage["effective_date"] = pd.to_datetime(mortgage["effective_date"], utc=True)
    history = pd.merge_asof(
        history.sort_values("valuation_date"), mortgage.sort_values("effective_date"),
        left_on="valuation_date", right_on="effective_date", direction="backward",
    )
    history["estimated_equity"] = [
        calculate_equity(value, balance)[0] if pd.notna(balance) else float("nan")
        for value, balance in zip(history["estimated_value"], history["principal_balance"])
    ]
    return history
