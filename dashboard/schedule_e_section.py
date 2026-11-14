"""Streamlit presentation for preliminary rental Schedule E worksheet.

All calculations are delegated to the read-only reporting engine.
"""
import pandas as pd
import streamlit as st

from src.services.schedule_e_report import schedule_e_report
from src.services.schedule_e_export import schedule_e_csv


def render_schedule_e(owner_db, mortgage_db, water_db, capital_db,
                      available_years):
    st.divider()
    st.subheader("Schedule E / Tax Reporting")
    st.caption(
        "Preliminary rental tax worksheet, not a completed tax return. "
        "Amounts reflect imported records across the selected calendar year, "
        "not the cash-flow dashboard's selected month."
    )
    years = sorted(set(int(y) for y in available_years), reverse=True)
    if not years:
        st.info("Import rental transactions to enable tax reporting.")
        return
    year = st.selectbox("Tax year", years, key="schedule_e_tax_year")
    try:
        report = schedule_e_report(
            year, owner_db=owner_db, mortgage_db=mortgage_db,
            water_db=water_db, capital_db=capital_db,
        )
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"Tax worksheet could not be generated: {exc}")
        return

    st.warning(
        "NOT FILING READY — depreciation and review items remain outstanding. "
        "The provisional difference below is not taxable rental profit."
    )

    summary = st.columns(4)
    summary[0].metric("Known rental income", f"${report['income']:,.2f}")
    summary[1].metric(
        "Known expenses (excl. depreciation)",
        f"${report['known_expenses_excluding_depreciation']:,.2f}",
    )
    summary[2].metric(
        "Provisional difference",
        f"${report['provisional_difference']:,.2f}",
    )
    summary[3].metric(
        "Capital spending (not deducted)",
        f"${report['capital_spending']:,.2f}",
    )

    with st.expander("Schedule E income and expense lines", expanded=True):
        lines = [
            {"Line": f"Line {number}", "Category": report["labels"][number],
             "Amount": amount}
            for number, amount in sorted(report["lines"].items())
        ]
        st.dataframe(
            pd.DataFrame(lines),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Amount": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
        st.caption(
            "Line 18 depreciation is not calculated. Some costs remain excluded "
            "pending review; do not use these totals as a filed return."
        )

    with st.expander(f"Capital improvements ({len(report['capital_improvements'])})"):
        if report["capital_improvements"]:
            assets = pd.DataFrame([
                {"Improvement": a["description"],
                 "Completed": a["completion_date"],
                 "Placed in service": a["placed_in_service_date"] or "Not confirmed",
                 "Cost": a["cost_cents"] / 100,
                 "Tax status": a["tax_treatment_status"]}
                for a in report["capital_improvements"]
            ])
            st.dataframe(
                assets, hide_index=True, use_container_width=True,
                column_config={"Cost": st.column_config.NumberColumn(format="$%.2f")},
            )
            st.caption(
                "Capital spending is displayed separately, not counted as an "
                "immediate Schedule E expense. Depreciation requires review."
            )
        else:
            st.info("No capital improvements recorded for this tax year.")

    with st.expander(f"Items requiring review ({len(report['review'])})"):
        for issue in report["review"]:
            st.write(f"• {issue}")

    st.download_button(
        "Download preliminary Schedule E CSV",
        data=schedule_e_csv(report),
        file_name=f"nesiaos_schedule_e_preview_{year}.csv",
        mime="text/csv",
        key=f"schedule_e_export_{year}",
    )
    st.caption(
        "CSV includes category totals, improvements, and review warnings. "
        "Export only when handling your private financial data appropriately."
    )
