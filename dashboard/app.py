"""NesiaOS unified rental dashboard (AppFolio + owner-paid mortgage).

Local only. Mortgage cash flow uses payment *effective* dates, not due dates.
Owner distributions are transfers received by the owner, not property expenses.
"""
from pathlib import Path
import os
import sqlite3

import pandas as pd
import streamlit as st

from src.services.financial_report import monthly_report, DEFAULT_DB_PATH
from src.services.water_report import read_bills, monthly_water_report
from src.services.water_importer import record_payment


st.set_page_config(page_title="NesiaOS", page_icon="🏠", layout="wide")

if st.query_params.get("page") == "privacy":
    st.title("NesiaOS Privacy Policy")
    st.markdown("""
Updated October 30, 2026

### Scope
This policy covers the NesiaOS personal Gmail bill importer.
The public NesiaOS dashboard uses fictional demonstration data
and does not connect to visitors' Gmail accounts.

### Gmail access and use
The local importer requests read-only Gmail access. This permission
allows reading mailbox contents; the application uses a search query
to find candidate utility-bill messages and PDF attachments.

It downloads matching PDFs and extracts utility account identifiers,
billing dates, service periods, charges, and balances for personal
property reporting. It does not send, delete, or modify email.

### Storage and sharing
Downloaded PDFs, extracted bill records, and Google authorization
tokens are stored on the computer running the importer. NesiaOS
does not intentionally upload this information to the public demo,
sell it, use it for advertising, or use it to train AI models.
Google processes authorization and Gmail API requests.

Google API data use follows the Google API Services User Data Policy,
including its Limited Use requirements.

### Retention and deletion
Local files remain until the user deletes them. Users can revoke
NesiaOS access in their Google Account's third-party connections.
Revoking access does not delete previously downloaded PDFs or records;
those must be deleted separately, along with any backups.

### Public website
The public demonstration is hosted by Streamlit. Website hosting
and technical usage data are subject to the hosting provider's policies.

### Contact
For questions, open an issue at
https://github.com/DocNessMonster/NesiaOS-Public/issues.
Do not include credentials, bills, or other private information.
""")
    st.stop()
    
st.title("NesiaOS")
st.subheader("Rental Property Dashboard")
st.markdown("[Privacy policy](?page=privacy)")
if os.environ.get("NESIAOS_PUBLIC_DEMO") == "1":
    st.info("PUBLIC DEMO — All statements, names, and financial figures are fictional.")
st.caption("AppFolio statements + mortgage history + water bills | All amounts in USD")

ROOT = Path(__file__).resolve().parents[1]
MORTGAGE_DB = Path(os.environ.get("NESIAOS_MORTGAGE_DB_PATH") or ROOT / "local_data" / "mortgage" / "mortgage.sqlite").expanduser()

WATER_DB = Path(os.environ.get("NESIAOS_WATER_DB_PATH") or ROOT / "local_data" / "water" / "water.sqlite").expanduser()
OWNER_DB = Path(os.environ.get("NESIAOS_DB_PATH") or DEFAULT_DB_PATH).expanduser()


def dollars(value):
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def metrics_grid(items):
    """Show six consistent metrics in two rows."""
    for start in (0, 3):
        columns = st.columns(3)
        for column, (label, amount) in zip(columns, items[start:start + 3]):
            column.metric(label, dollars(amount))


# --- AppFolio data (existing verified report) ---
report = monthly_report().copy()
expected = {"month", "operating_income", "operating_expenses", "owner_distributions"}
if report.empty or not expected.issubset(report.columns):
    st.error("The AppFolio report is empty or is missing required columns.")
    st.stop()

report["month"] = pd.to_datetime(report["month"].astype(str), errors="coerce").dt.strftime("%Y-%m")
if report["month"].isna().any():
    st.error("Could not read some AppFolio reporting months.")
    st.stop()

# --- Mortgage data (imported and validated locally) ---
if not MORTGAGE_DB.is_file():
    st.error(f"Mortgage database not found: {MORTGAGE_DB}")
    st.stop()

with sqlite3.connect(MORTGAGE_DB) as connection:
    events = pd.read_sql_query(
        """SELECT effective_date, event_type, category, payment_amount,
                  principal_paid, interest_paid, escrow_contribution,
                  escrow_disbursement, principal_balance
           FROM mortgage_events""",
        connection,
    )

if events.empty:
    st.error("Mortgage database contains no events.")
    st.stop()
if events["category"].eq("unclassified_escrow_disbursement").any():
    st.error("An unclassified escrow disbursement needs review before reporting.")
    st.stop()

events["effective_date"] = pd.to_datetime(events["effective_date"], errors="coerce")
if events["effective_date"].isna().any():
    st.error("The mortgage database contains an invalid transaction date.")
    st.stop()
events["month"] = events["effective_date"].dt.strftime("%Y-%m")

payments = events.loc[events["event_type"] == "mortgage_payment"].copy()
escrow_events = events.loc[events["event_type"] == "escrow_disbursement"].copy()
if payments.empty:
    st.error("No mortgage payments were found.")
    st.stop()

mortgage_monthly = payments.groupby("month", as_index=False).agg(
    mortgage_payment=("payment_amount", "sum"),
    principal_paid=("principal_paid", "sum"),
    interest_paid=("interest_paid", "sum"),
    escrow_contribution=("escrow_contribution", "sum"),
)

# Do not invent zero-dollar mortgage payments for months without a statement.
combined = report.merge(mortgage_monthly, on="month", how="inner")
combined = combined.sort_values("month").reset_index(drop=True)
if combined.empty:
    st.error("There are no months with both AppFolio and mortgage data.")
    st.stop()

# Utility receipts already belong to AppFolio income/distributions; never add again.
try:
    water_bills = read_bills(WATER_DB)
    water_monthly = monthly_water_report(WATER_DB, OWNER_DB)
except (ValueError, sqlite3.Error) as exc:
    st.error(f"Water records need review: {exc}")
    st.stop()
combined = combined.merge(water_monthly, on="month", how="left")
water_columns = ["water_billed", "water_paid", "utility_reimbursements", "unconfirmed_bills"]
combined[water_columns] = combined[water_columns].fillna(0)

# Cash actually reaching the owner, minus payments from the owner's bank account.
# This is NOT the same as property operating cash flow.
combined["actual_cash_flow"] = (
    combined["owner_distributions"] - combined["mortgage_payment"] - combined["water_paid"]
).round(2)

missing_appfolio = sorted(set(mortgage_monthly["month"]) - set(report["month"]))
missing_mortgage = sorted(set(report["month"]) - set(mortgage_monthly["month"]))
if missing_appfolio or missing_mortgage:
    st.caption(
        "Only months with BOTH statements are included. "
        + (f"Awaiting AppFolio: {', '.join(missing_appfolio)}. " if missing_appfolio else "")
        + (f"Awaiting mortgage records: {', '.join(missing_mortgage)}." if missing_mortgage else "")
    )

months = combined["month"].tolist()
selected_month = st.selectbox(
    "Reporting month",
    options=months,
    index=len(months) - 1,
    format_func=lambda month: pd.Period(month, freq="M").strftime("%B %Y"),
)
selected = combined.loc[combined["month"] == selected_month].iloc[0]
selected_year = selected_month[:4]
ytd = combined.loc[
    (combined["month"].str.startswith(selected_year))
    & (combined["month"] <= selected_month)
]

def summary_items(frame):
    return [
        ("Actual cash flow", frame["actual_cash_flow"]),
        ("Operating income (incl. reimbursements)", frame["operating_income"]),
        ("Operating expenses", frame["operating_expenses"]),
        ("Mortgage payments", frame["mortgage_payment"]),
        ("Principal paid", frame["principal_paid"]),
        ("Interest paid", frame["interest_paid"]),
    ]


st.subheader(f"Monthly Overview — {pd.Period(selected_month, 'M').strftime('%B %Y')}")
metrics_grid(summary_items(selected))

st.divider()
st.subheader(f"{selected_year} Year-to-Date — Through {pd.Period(selected_month, 'M').strftime('%B')}")
metrics_grid(summary_items(ytd.sum(numeric_only=True)))

st.divider()
st.subheader("Actual Monthly Cash Flow")
st.caption("Owner distributions received minus mortgage and confirmed water payments. Unconfirmed water payments are excluded.")
st.bar_chart(
    combined.set_index("month")[["actual_cash_flow"]].rename(
        columns={"actual_cash_flow": "Actual cash flow"}
    ),
    color="#419C91",
    use_container_width=True,
)

st.subheader("Monthly Cash Outflow Breakdown")
st.caption("Stacked monthly expenses and mortgage components; principal is debt repayment, not an expense.")
st.bar_chart(
    combined.set_index("month")[[
        "operating_expenses", "principal_paid", "interest_paid", "escrow_contribution", "water_paid"
    ]].rename(columns={
        "operating_expenses": "Operating expenses",
        "principal_paid": "Principal",
        "interest_paid": "Interest",
        "escrow_contribution": "Escrow contribution",
        "water_paid": "Confirmed water payments",
    }),
    stack=True,
    color=["#4C8DCE", "#E7A449", "#9876BB", "#59A98E", "#327C9C"],
    use_container_width=True,
)

st.divider()
st.subheader("Water Bills & Utility Reimbursements")
water_cols = st.columns(3)
water_cols[0].metric("Water charges billed", dollars(selected["water_billed"]))
water_cols[1].metric("Utility reimbursements received", dollars(selected["utility_reimbursements"]))
water_cols[2].metric("Confirmed water payments", dollars(selected["water_paid"]))
st.caption(
    "Charges use the bill month; payments use the confirmed payment date; "
    "reimbursements use the AppFolio statement month and are already included in income. "
    "Receipts are not automatically matched to individual bills, so a monthly difference "
    "does not establish what a tenant owes."
)
if WATER_DB.is_file():
    visible_bills = water_bills.loc[water_bills["bill_date"].str[:7] <= selected_month].copy()
    pending_count = visible_bills["payment_date"].isna().sum()
    if pending_count:
        st.warning(f"{pending_count} imported bill(s) through this month have no confirmed payment. "
                   "Cash flow excludes those payments until confirmed.")
    st.dataframe(visible_bills.drop(columns=["bill_id"]).rename(columns={
        "bill_date": "Bill date", "due_date": "Due date", "service_start": "Service start",
        "service_end": "Service end", "water": "Water", "wastewater": "Wastewater", "solid_waste": "Trash",
        "balance_forward": "Previous balance", "adjustments": "Adjustments", "payment_date": "Payment date",
        "current_charges": "Current charges", "total_due": "Total due", "payment_amount": "Confirmed amount paid"
    }), hide_index=True, use_container_width=True, column_config={
        name: st.column_config.NumberColumn(format="$%.2f")
        for name in ("Water", "Wastewater", "Trash", "Previous balance", "Adjustments",
                     "Current charges", "Total due", "Confirmed amount paid")
    })
    if not water_monthly.empty:
        st.bar_chart(water_monthly.loc[water_monthly["month"] <= selected_month].set_index("month")[[
            "water_billed", "utility_reimbursements", "water_paid"
        ]].rename(columns={"water_billed": "Charges billed", "utility_reimbursements": "Reimbursements received",
                           "water_paid": "Confirmed payments"}), stack=False)
    if os.environ.get("NESIAOS_PUBLIC_DEMO") != "1":
        with st.expander("Confirm a water bill payment"):
            st.caption("Enter the date and full amount actually paid. Autopay alone does not confirm a payment. "
                       "Partial or combined payments need separate review.")
            unpaid = water_bills.loc[water_bills["payment_date"].isna()]
            if unpaid.empty:
                st.write("No bills awaiting payment confirmation.")
            else:
                choices = unpaid["bill_id"].tolist()
                labels = {r["bill_id"]: f"{r['bill_date']} | charges {dollars(r['current_charges'])} | due {dollars(r['total_due'])}"
                          for r in unpaid.to_dict("records")}
                with st.form("water_payment"):
                    bill_id = st.selectbox("Bill", choices, format_func=lambda key: labels[key])
                    paid_on = st.date_input("Actual payment date")
                    paid_amount = st.number_input("Actual full payment amount", min_value=0.0, step=0.01)
                    submitted = st.form_submit_button("Record confirmed payment")
                if submitted:
                    try:
                        record_payment(WATER_DB, bill_id, paid_on.isoformat(), paid_amount)
                    except (ValueError, sqlite3.Error) as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
else:
    st.info("No water database found yet. Import bills to populate this section.")

st.divider()
st.subheader("Mortgage & Escrow Details")
selected_month_end = pd.Period(selected_month, freq="M").end_time
balance_as_of = payments.loc[payments["effective_date"] <= selected_month_end].sort_values("effective_date")
if not balance_as_of.empty:
    latest_payment = balance_as_of.iloc[-1]
    balance_col, escrow_col = st.columns(2)
    balance_col.metric("Remaining mortgage principal", dollars(latest_payment["principal_balance"]))
    balance_col.caption(f"As of {latest_payment['effective_date']:%B %d, %Y}")
else:
    escrow_col = st.container()

ytd_escrow = escrow_events.loc[
    (escrow_events["month"].str.startswith(selected_year))
    & (escrow_events["month"] <= selected_month)
]
tax_paid = ytd_escrow.loc[ytd_escrow["category"] == "property_tax", "escrow_disbursement"].sum()
insurance_paid = ytd_escrow.loc[ytd_escrow["category"] == "hazard_insurance", "escrow_disbursement"].sum()
with escrow_col:
    st.metric("Taxes paid from escrow (YTD)", dollars(tax_paid))
    st.metric("Insurance paid from escrow (YTD)", dollars(insurance_paid))

st.subheader("Monthly Financial Details")
monthly_details = combined.loc[combined["month"] <= selected_month, [
        "month", "operating_income", "operating_expenses", "owner_distributions",
        "mortgage_payment", "principal_paid", "interest_paid", "escrow_contribution",
        "actual_cash_flow", "water_billed", "water_paid", "utility_reimbursements",
    ]].rename(columns={
        "month": "Month",
        "operating_income": "Operating income (incl. reimbursements)",
        "operating_expenses": "Operating expenses",
        "owner_distributions": "Owner distributions",
        "mortgage_payment": "Mortgage payment",
        "principal_paid": "Principal",
        "interest_paid": "Interest",
        "escrow_contribution": "Escrow contribution",
        "actual_cash_flow": "Actual cash flow",
        "water_billed": "Water charges billed",
        "water_paid": "Confirmed water payments",
        "utility_reimbursements": "Utility reimbursements (already in income)",
    })
st.dataframe(
    monthly_details.style.format(
        {column: dollars for column in monthly_details.columns if column != "Month"},
        na_rep="—",
    ),
    use_container_width=True,
    hide_index=True,
)

st.info(
    "Actual cash flow = AppFolio owner distributions − mortgage payments − confirmed water payments. "
    "Water bills without a confirmed payment date and amount are excluded from cash flow. "
    "Other personally paid rental expenses are not yet included. "
    "Mortgage principal builds equity; escrow disbursements (taxes/insurance) "
    "are not subtracted a second time. "
    "Year-to-date totals use only months available in BOTH data sources."
)

