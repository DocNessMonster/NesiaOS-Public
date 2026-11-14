"""Interactive *synthetic* residential rental depreciation scenarios for the public demo.

The panel is deliberately isolated from production databases, source PDFs,
and the actual Schedule E reporting engine. All defaults are fictional.
"""
from datetime import date

import pandas as pd
import streamlit as st

from src.services.depreciation_scenarios import RentalDepreciationScenario


def render_depreciation_demo():
    st.divider()
    st.subheader("Depreciation & Prior-Year Reconciliation — Demo")
    st.info(
        "FICTIONAL EXAMPLE — explore how home-to-rental conversion, qualifying "
        "renovations, and a later building improvement affect depreciation. "
        "This calculator does not modify records or populate Schedule E Line 18."
    )

    with st.expander("Adjust fictional property assumptions", expanded=False):
        left, right = st.columns(2)
        with left:
            purchase = st.number_input(
                "Original purchase price ($)", min_value=1.0, value=180000.0,
                step=1000.0, key="demo_dep_purchase"
            )
            acquisition_costs = st.number_input(
                "Eligible purchase closing costs ($)", min_value=0.0, value=850.0,
                step=50.0, key="demo_dep_closing"
            )
            acquisition_building = st.slider(
                "Building allocation at acquisition (%)",
                min_value=1, max_value=100, value=76, key="demo_dep_purchase_share"
            )
            renovation = st.number_input(
                "Qualifying pre-rental improvements ($)", min_value=0.0,
                value=24000.0, step=500.0, key="demo_dep_renovation"
            )
        with right:
            fmv = st.number_input(
                "Fair market value at rental conversion ($)", min_value=1.0,
                value=290000.0, step=1000.0, key="demo_dep_fmv"
            )
            conversion_building = st.slider(
                "Building allocation of conversion FMV (%)",
                min_value=1, max_value=100, value=76, key="demo_dep_fmv_share"
            )
            service_date = st.date_input(
                "Original rental placed-in-service date",
                value=date(2025, 5, 1), key="demo_dep_service"
            )
            roof_cost = st.number_input(
                "Subsequent building improvement ($)", min_value=0.0,
                value=12500.0, step=500.0, key="demo_dep_roof"
            )
            roof_date = st.date_input(
                "Improvement placed-in-service date",
                value=date(2026, 8, 15), key="demo_dep_roof_service"
            )

    try:
        scenario = RentalDepreciationScenario(
            acquisition_price=purchase,
            acquisition_closing_costs=acquisition_costs,
            acquisition_building_pct=acquisition_building,
            pre_rental_improvements=renovation,
            conversion_fmv=fmv,
            conversion_building_pct=conversion_building,
            original_placed_in_service=service_date,
            improvement_cost=roof_cost,
            improvement_placed_in_service=roof_date if roof_cost else None,
        )
        reports = [scenario.calculate(year) for year in (2025, 2026)]
    except ValueError as exc:
        st.warning(f"Scenario inputs require review: {exc}")
        return

    basis = reports[-1]
    metrics = st.columns(3)
    metrics[0].metric(
        "Adjusted building basis (example)",
        f"${basis['adjusted_building_basis']:,.2f}",
    )
    metrics[1].metric(
        "Building FMV at conversion (example)",
        f"${basis['conversion_fmv_building']:,.2f}",
    )
    metrics[2].metric(
        "Depreciable house basis (lower)",
        f"${basis['depreciable_house_basis']:,.2f}",
    )
    st.caption(
        "The lower-of-adjusted-basis-or-FMV rule applies to the building. "
        "Land is excluded. All allocations and eligible costs require evidence."
    )

    table = pd.DataFrame([
        {
            "Tax year": item["year"],
            "Original house": float(item["house_depreciation"]),
            "Subsequent improvement": float(item["improvement_depreciation"]),
            "Combined estimated depreciation": float(item["total_depreciation"]),
        }
        for item in reports
    ])
    st.dataframe(
        table, hide_index=True, use_container_width=True,
        column_config={
            "Original house": st.column_config.NumberColumn(format="$%.2f"),
            "Subsequent improvement": st.column_config.NumberColumn(format="$%.2f"),
            "Combined estimated depreciation": st.column_config.NumberColumn(format="$%.2f"),
        },
    )

    with st.expander("Example of reviewing a previously filed year"):
        fictional_filed = st.number_input(
            "Previously claimed depreciation for 2025 ($) — fictional",
            min_value=0.0, value=2200.0, step=100.0, key="demo_dep_filed"
        )
        difference = float(reports[0]["total_depreciation"]) - fictional_filed
        st.metric(
            "Illustrative 2025 difference (estimated minus previously filed)",
            f"${difference:+,.2f}",
        )
        st.caption(
            "A difference is a REVIEW FLAG, not a conclusion that an amended "
            "return is required. Other expense classifications, passive loss "
            "limits, tax basis and supporting documentation must also be reviewed."
        )

    st.warning(
        "NOT FILING READY — simplified 27.5-year straight-line, mid-month "
        "calculations for 2025–2026 only. This tool does not cover final-year "
        "dispositions, unrecaptured depreciation, partial business use, special "
        "elections, or the complete MACRS lifetime schedule. "
        "No fictional depreciation is written into tax reports."
    )
