"""Synthetic calculations for rental conversion, 2025 and 2026 depreciation."""
from datetime import date
from decimal import Decimal

import pytest

from src.services.depreciation_scenarios import (
    RentalDepreciationScenario, mid_month_fraction,
)


def scenario(**overrides):
    args = dict(
        acquisition_price="180000.00",
        acquisition_closing_costs="850.00",
        acquisition_building_pct="76",
        pre_rental_improvements="24000.00",
        conversion_fmv="290000.00",
        conversion_building_pct="76",
        original_placed_in_service=date(2025, 5, 1),
        improvement_cost="12500.00",
        improvement_placed_in_service=date(2026, 8, 15),
    )
    args.update(overrides)
    return RentalDepreciationScenario(**args)


def test_pre_rental_renovations_augment_building_basis_once():
    r = scenario()
    old = r.calculate(2025)
    new = r.calculate(2026)
    assert old["adjusted_building_basis"] == Decimal("161446.00")
    assert old["conversion_fmv_building"] == Decimal("220400.00")
    assert old["depreciable_house_basis"] == Decimal("161446.00")
    assert old["limiting_basis"] == "adjusted_cost"
    assert old["house_depreciation"] == Decimal("3669.23")
    assert old["improvement_depreciation"] == Decimal("0.00")
    assert new["house_depreciation"] == Decimal("5870.76")
    assert new["improvement_depreciation"] == Decimal("170.45")
    assert new["total_depreciation"] == Decimal("6041.21")


def test_conversion_fmv_lower_than_adjusted_cost_basis_controls():
    r = scenario(conversion_fmv="120000.00")
    annual = r.calculate(2026)
    assert annual["depreciable_house_basis"] == Decimal("91200.00")
    assert annual["limiting_basis"] == "conversion_fmv"
    assert annual["house_depreciation"] == Decimal("3316.36")


def test_first_year_mid_month_fraction():
    assert mid_month_fraction(date(2025, 5, 1), 2025) == Decimal("7.5") / 12
    assert mid_month_fraction(date(2026, 8, 30), 2026) == Decimal("4.5") / 12
    assert mid_month_fraction(date(2026, 8, 1), 2025) == 0
    assert mid_month_fraction(date(2025, 5, 1), 2026) == 1


@pytest.mark.parametrize("updates", [
    {"acquisition_price": "-1"},
    {"conversion_building_pct": "101"},
    {"acquisition_building_pct": "0"},
    {"acquisition_closing_costs": "NaN"},
    {"improvement_cost": "100", "improvement_placed_in_service": None},
])
def test_invalid_assumptions_rejected(updates):
    with pytest.raises(ValueError):
        scenario(**updates).calculate(2026)


def test_no_improvement_has_zero_roof_depreciation():
    r = scenario(improvement_cost="0", improvement_placed_in_service=None)
    assert r.calculate(2025)["improvement_depreciation"] == 0
    assert r.calculate(2026)["improvement_depreciation"] == 0


def test_public_entrypoint_only_renders_synthetic_assumptions():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "streamlit_app.py"),
        default_timeout=30,
    ).run()
    assert not app.exception
    headers = [h.value for h in app.subheader]
    assert "Depreciation & Prior-Year Reconciliation — Demo" in headers
    assert len(app.warning) > 0
    table = [
        frame.value for frame in app.dataframe
        if "Combined estimated depreciation" in frame.value.columns
    ]
    assert len(table) == 1
    assert table[0]["Tax year"].tolist() == [2025, 2026]
    assert round(table[0]["Subsequent improvement"].iloc[0], 2) == 0
    assert round(table[0]["Subsequent improvement"].iloc[1], 2) == 170.45
