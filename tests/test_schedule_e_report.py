"""Synthetic Schedule E worksheet tests; never use production databases."""
import sqlite3

from src.services.schedule_e_report import schedule_e_report


def test_schedule_e_maps_sources_without_double_counting(tmp_path):
    owner = tmp_path / "owner.sqlite"
    mortgage = tmp_path / "mortgage.sqlite"
    water = tmp_path / "missing_water.sqlite"
    capital = tmp_path / "capital.sqlite"

    with sqlite3.connect(owner) as conn:
        conn.execute("CREATE TABLE transactions (date TEXT, category TEXT, "
                     "flow_type TEXT, income REAL, expense REAL, description TEXT)")
        conn.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?)", [
            ("2026-08-01", "rent_income", "income", 2000, 0, "Rent"),
            ("2026-08-02", "utility_reimbursement", "income", 75, 0, "Utility reimbursement"),
            ("2026-08-03", "management_fee", "operating_expense", 0, 200, "Manager"),
            ("2026-08-04", "owner_distribution", "transfer", 0, 1800, "Owner transfer"),
            ("2026-08-05", "sales_tax", "operating_expense", 0, 10, "Tax - Sales"),
            ("2025-01-01", "rent_income", "income", 999, 0, "Rent"),
        ])
    with sqlite3.connect(mortgage) as conn:
        conn.execute("CREATE TABLE mortgage_events "
                     "(effective_date TEXT, event_type TEXT, category TEXT, "
                     "interest_paid REAL, escrow_disbursement REAL)")
        conn.executemany("INSERT INTO mortgage_events VALUES (?,?,?,?,?)", [
            ("2026-08-05", "mortgage_payment", "regular_payment", 250, 0),
            ("2026-08-05", "escrow_disbursement", "property_tax", 0, 300),
            ("2026-08-06", "escrow_disbursement", "hazard_insurance", 0, 100),
        ])
    with sqlite3.connect(capital) as conn:
        conn.execute("CREATE TABLE capital_improvements (asset_id TEXT PRIMARY KEY, "
                     "description TEXT, cost_cents INTEGER, completion_date TEXT, "
                     "placed_in_service_date TEXT, payment_date TEXT, payment_source TEXT, "
                     "asset_type TEXT, tax_treatment_status TEXT, notes TEXT)")
        conn.execute("INSERT INTO capital_improvements VALUES (?,?,?,?,?,?,?,?,?,?)",
                     ("roof", "Roof replacement", 1512000, "2026-08-30",
                      "2026-08-30", None, "owner_direct", "roof", "pending_review", ""))

    result = schedule_e_report(2026, owner, mortgage, water, capital)
    assert result["income"] == 2075
    assert result["lines"][11] == 200
    assert result["lines"][12] == 250
    assert result["lines"][16] == 300
    assert result["lines"][9] == 100
    assert result["known_expenses_excluding_depreciation"] == 850
    assert result["provisional_difference"] == 1225
    assert result["capital_spending"] == 15120
    assert any("sales_tax" in item for item in result["review"])
    assert result["filing_ready"] is False
