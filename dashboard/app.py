
import streamlit as st

from src.services.financial_report import monthly_report


st.set_page_config(
    page_title="NesiaOS",
    page_icon="🏠",
    layout="wide",
)

st.title("NesiaOS")
st.subheader("Rental Property Dashboard")

st.caption(
    "Financial performance from AppFolio statements. "
    "Excludes mortgage payments and other externally paid expenses."
)

# Load the verified financial data
report = monthly_report()

# Calculate dashboard metrics
income = report["operating_income"].sum()
expenses = report["operating_expenses"].sum()
cash_flow = report["operating_cash_flow"].sum()
distributions = report["owner_distributions"].sum()

# Summary metrics
col1, col2, col3, col4 = st.columns(4)

col1.metric("Operating Income", f"${income:,.2f}")
col2.metric("Operating Expenses", f"${expenses:,.2f}")
col3.metric("Operating Cash Flow", f"${cash_flow:,.2f}")
col4.metric("Owner Distributions", f"${distributions:,.2f}")

st.divider()

# Monthly financial charts
st.subheader("Monthly Operating Performance")

st.bar_chart(
    report.set_index("month")[
        ["operating_income", "operating_expenses"]
    ]
)

st.subheader("Monthly Operating Cash Flow")

st.line_chart(
    report.set_index("month")["operating_cash_flow"]
)

st.divider()

# Detailed financial table
st.subheader("Monthly Financial Details")

st.dataframe(
    report,
    use_container_width=True,
    hide_index=True,
)

st.info(
    "Operating cash flow = income minus property operating expenses. "
    "Owner distributions are transfers, not expenses. "
    "Mortgage payments and owner-paid costs are not yet included."
)
