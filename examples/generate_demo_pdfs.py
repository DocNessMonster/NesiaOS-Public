"""Generate fully synthetic PDFs for NesiaOS public portfolio demonstrations.

This script is intentionally self-contained. It never reads a bank statement,
user record, actual mortgage, or any non-demo financial data.

Dependency: reportlab.  Run: python examples/generate_demo_pdfs.py
"""
from __future__ import annotations

import calendar
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table, TableStyle

OUT = Path(__file__).resolve().parent
YEAR = 2026
MONTHS = (4, 5, 6, 7, 8, 9)
D = Decimal
RENT = D("2350.00")
MANAGEMENT_FEE = D("211.50")
MONTH_EXTRAS = {
    4: [],
    5: [(12, "Sample Plumbing", "EFT", "Plumbing Maintenance - Demo faucet repair", D("0"), D("180"))],
    6: [(14, "Sample Tenant", "Receipt", "Utilities Reimbursement - Demo water bill", D("75"), D("0"))],
    7: [(19, "Sample Plumbing", "EFT", "Plumbing Maintenance - DEMO emergency repair", D("0"), D("1360"))],
    8: [(12, "Sample Landscapers", "EFT", "Landscaping Yard Care - DEMO cleanup", D("0"), D("90")),
        (18, "Sample Service", "EFT", "Tax - Sales - DEMO services", D("0"), D("30"))],
    9: [],
}
OPENING_CASH = D("600.00")


def usd(value: Decimal | None) -> str:
    return f"{value:,.2f}" if value is not None else ""


def _canvas(path: Path, pagesize: tuple, title: str) -> Canvas:
    c = Canvas(str(path), pagesize=pagesize, pageCompression=1)
    c.setTitle(title)
    c.setAuthor("NesiaOS - SYNTHETIC DEMO")
    c.setSubject("Entirely invented demonstration data; not a financial statement")
    return c


def appfolio_rows(month: int):
    """Create an owner-statement ledger that reconciles to the cent."""
    month_str = calendar.month_name[month]
    opening = OPENING_CASH
    running = opening
    ledger = [
        (3, "Demo Tenant", "Receipt", f"RENT-{month:02d}", f"Rent Income - {month_str} {YEAR}", RENT, D("0")),
        (7, "Fictional Property Co.", "EFT", f"MGMT-{month:02d}", f"Management Fees - {month_str} {YEAR}", D("0"), MANAGEMENT_FEE),
    ]
    for idx, (day, payee, kind, description, income, expense) in enumerate(MONTH_EXTRAS[month], 1):
        ledger.append((day, payee, kind, f"EXTRA-{month:02d}-{idx}", description, income, expense))
    ledger.sort(key=lambda rec: rec[0])
    total_income = sum((r[5] for r in ledger), D("0"))
    expenses_excluding_distribution = sum((r[6] for r in ledger), D("0"))
    distribution = total_income - expenses_excluding_distribution
    if distribution < 0:
        raise ValueError("Demo reserve would be insufficient")
    ledger.append((26, "Example Owner", "eCheck", f"DIST-{month:02d}", f"Owner Draws - DEMO owner payment for {month:02d}/{YEAR}", D("0"), distribution))

    data = [["Date", "Payee / Payer", "Type", "Reference", "Description", "Income", "Expense", "Balance"]]
    data.append(["", "", "", "", f"Beginning Cash Balance as of {month:02d}/01/{YEAR}", "", "", usd(opening)])
    for day, payee, kind, ref, desc, inc, exp in ledger:
        running += inc - exp
        data.append([f"{month:02d}/{day:02d}/{YEAR}", payee, kind, ref, desc,
                     usd(inc) if inc else "", usd(exp) if exp else "", usd(running)])
    data.append(["", "", "", "", "Ending Cash Balance", "", "", usd(running)])
    total_expense = expenses_excluding_distribution + distribution
    data.append([f"Total {usd(total_income)} {usd(total_expense)}", "", "", "", "", "", "", ""])
    assert running == opening, (month, running)
    assert total_income == total_expense
    return data


def build_owner_pdf(month: int) -> Path:
    month_name = calendar.month_name[month]
    output = OUT / f"demo_owner_statement_{YEAR}_{month:02d}.pdf"
    page_w, page_h = (900, 612)
    c = _canvas(output, (page_w, page_h), f"SYNTHETIC Owner Statement - {month_name} {YEAR}")
    c.setFillColor(colors.HexColor("#142e47"))
    c.rect(0, page_h - 85, page_w, 85, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.white)
    c.drawString(28, page_h - 35, "SYNTHETIC PROPERTY MANAGEMENT STATEMENT")
    c.setFont("Helvetica", 10)
    c.drawString(28, page_h - 53, "Sample Property Management  |  DEMO DATA ONLY - NOT ISSUED BY APPFOLIO")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#22354a"))
    c.drawString(28, page_h - 113, f"Period: 01 {month_name[:3]} {YEAR} - {calendar.monthrange(YEAR,month)[1]} {month_name[:3]} {YEAR}")
    c.setFont("Helvetica", 10)
    c.drawString(28, page_h - 132, "Property: Example Rental Property - fictional and not a real address")
    c.drawString(28, page_h - 148, "Owner: Example Owner (fictional)  |  All names, references and dollar amounts are invented")

    data = appfolio_rows(month)
    tbl = Table(data, colWidths=[135, 115, 60, 78, 225, 76, 76, 75],
                rowHeights=[27] + [25] * (len(data) - 1))
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#244b6a")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("ALIGN", (5,1), (7,-1), "RIGHT"),
        ("BACKGROUND", (0,-2), (-1,-1), colors.HexColor("#edf4f7")),
        ("FONTNAME", (0,-1), (0,-1), "Helvetica-Bold"),
    ]))
    w,h=tbl.wrapOn(c, 840, 400)
    tbl.drawOn(c, (page_w-w)/2, page_h-173-h)
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.HexColor("#576c7d"))
    c.drawString(28, 31, "NesiaOS public demo fixture - generated from fictional ledger entries, not from a real owner's documents.")
    c.save()
    return output


MORTGAGE_AMOUNT = D("1128.45")
ESCROW_PAYMENT = D("290.00")
PRINCIPAL_FIRST = D("425.00")
PRINCIPAL_INCREASE = D("1.05")
PRINCIPAL_BEGINNING = D("145000.00")
ESCROW_BEGINNING = D("950.00")

@dataclass
class MortgageEvent:
    effective: date
    due: date
    description: str
    total: Decimal
    principal: Decimal
    principal_balance: Decimal
    interest: Decimal
    escrow: Decimal
    escrow_balance: Decimal


def mortgage_events() -> list[MortgageEvent]:
    """Generate coherent fake balances and fake escrow disbursements."""
    events: list[MortgageEvent] = []
    principal_balance = PRINCIPAL_BEGINNING
    escrow_balance = ESCROW_BEGINNING
    for i, month in enumerate(MONTHS):
        principal = PRINCIPAL_FIRST + PRINCIPAL_INCREASE * i
        interest = MORTGAGE_AMOUNT - ESCROW_PAYMENT - principal
        principal_balance -= principal
        escrow_balance += ESCROW_PAYMENT
        events.append(MortgageEvent(date(YEAR, month, 5), date(YEAR, month, 1),
            f"Loan Payment due={month}/1/{YEAR}", MORTGAGE_AMOUNT, -principal,
            principal_balance, interest, ESCROW_PAYMENT, escrow_balance))
        if month == 5:
            amt = D("975.00")
            escrow_balance -= amt
            events.append(MortgageEvent(date(YEAR, month, 25), date(YEAR, month, 1),
                "Escrow disbursement - property tax", -amt, D("0"),
                principal_balance, D("0"), -amt, escrow_balance))
        if month == 8:
            amt = D("720.00")
            escrow_balance -= amt
            events.append(MortgageEvent(date(YEAR, month, 25), date(YEAR, month, 1),
                "Escrow disbursement - insurance", -amt, D("0"),
                principal_balance, D("0"), -amt, escrow_balance))
    assert principal_balance == PRINCIPAL_BEGINNING - sum((PRINCIPAL_FIRST + PRINCIPAL_INCREASE * i for i in range(len(MONTHS))), D("0"))
    return list(reversed(events))


MORTGAGE_ROWS = [
    "Unapplied bal", "Unapplied amt", "Fee bal", "Fee amt", "Late chg bal", "Late chg amt",
    "Curtailment bal", "Escrow bal", "Escrow amt", "Interest amt", "Principal bal",
    "Principal amt", "Transaction amt", "Transaction", "Payment due", "Effective date",
]
MORTGAGE_ROW_HEIGHTS = [43]*13 + [143,35,35]


def _date_short(dt: date) -> str:
    return f"{dt.month}/{dt.day}/{dt.year % 100:02d}"


def _mortgage_cell(e: MortgageEvent, row: int) -> str:
    if row == 15:
        return _date_short(e.effective)
    if row == 14:
        return _date_short(e.due)
    if row == 13:
        return e.description
    if row == 12:
        return f"${usd(e.total)}" if e.total >= 0 else f"(${usd(-e.total)})"
    if row == 11:
        return f"(${usd(-e.principal)})" if e.principal < 0 else f"${usd(e.principal)}"
    if row == 10:
        return f"${usd(e.principal_balance)}"
    if row == 9:
        return f"${usd(e.interest)}"
    if row == 8:
        return f"(${usd(-e.escrow)})" if e.escrow < 0 else f"${usd(e.escrow)}"
    if row == 7:
        return f"${usd(e.escrow_balance)}"
    return "$0.00"


def build_mortgage_pdf() -> Path:
    """Use a rotated field table matching the PDF geometry the importer expects.

    This PDF is drawn from scratch. No real mortgage PDF is used as a template.
    """
    output = OUT / "demo_mortgage_payment_history_2026.pdf"
    page_w, page_h = 612, 842
    c = _canvas(output, (page_w, page_h), "SYNTHETIC Mortgage Payment History 2026")
    c.setFillColor(colors.HexColor("#162c43"))
    c.rect(0, 795, page_w, 47, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(35, 820, "SYNTHETIC MORTGAGE PAYMENT HISTORY")
    c.setFont("Helvetica", 9)
    c.drawString(35, 805, "FICTIONAL LENDER - Demo only / no real account information")

    events = mortgage_events()
    table_left = 34
    xedges = [table_left + 25*j for j in range(len(events)+2)]
    yedges = [52]
    for height in MORTGAGE_ROW_HEIGHTS:
        yedges.append(yedges[-1]+height)
    assert yedges[-1] == 824
    c.setStrokeColor(colors.HexColor("#a7b7c7"))
    c.setLineWidth(.4)
    for y in yedges:
        c.line(xedges[0], page_h-y, xedges[-1], page_h-y)
    for x in xedges:
        c.line(x, page_h-yedges[0], x, page_h-yedges[-1])

    for row,label in enumerate(MORTGAGE_ROWS):
        for col in range(len(events)+1):
            s = label if col == 0 else _mortgage_cell(events[col-1], row)
            # The real file's cells contain 90-degree text. The importer
            # reverses extraction order; use natural text in this rotation.
            x=xedges[col]
            top,bottom=yedges[row],yedges[row+1]
            c.saveState()
            c.translate(x+16, page_h-bottom+5)
            c.rotate(90)
            c.setFillColor(colors.HexColor("#17354c"))
            c.setFont("Helvetica", 5.0 if col == 0 else 6.3)
            c.drawString(0, 0, s)
            c.restoreState()

    # Reader-friendly demo summary in unused space (doesn't alter table).
    panel_x = xedges[-1] + 22
    c.setFillColor(colors.HexColor("#20374d"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(panel_x, 735, "DEMO SUMMARY")
    c.setFont("Helvetica", 10)
    details = [
        "100% INVENTED DATA", "",
        "Apr-Sep 2026", "Six monthly payments", "Two escrow disbursements", "",
        "Monthly payment:", "$1,128.45", "",
        "Monthly escrow:", "$290.00", "",
        "No actual loan", "numbers or owner", "information included.", "",
        "Rotate the table view", "to inspect each event.",
    ]
    y = 706
    for entry in details:
        c.drawString(panel_x, y, entry)
        y -= 19
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#697b8a"))
    c.drawString(panel_x, 140, "Made for importer")
    c.drawString(panel_x, 127, "compatibility testing.")
    c.save()
    return output


def build_expected_totals() -> Path:
    """Write source-of-truth expected monthly totals for fixture verification."""
    result = OUT / "demo_expected_totals.csv"
    all_events = mortgage_events()
    by_month = {event.effective.month: event for event in all_events if event.total > 0}
    columns = [
        "month", "rental_income", "operating_expenses", "owner_distributions",
        "mortgage_payment", "principal_paid", "interest_paid", "escrow_contribution",
        "actual_cash_flow",
    ]
    with result.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for month in MONTHS:
            extra_income = sum((inc for _, _, _, _, inc, _ in MONTH_EXTRAS[month]), D("0"))
            extra_expenses = sum((exp for _, _, _, _, _, exp in MONTH_EXTRAS[month]), D("0"))
            income = RENT + extra_income
            expenses = MANAGEMENT_FEE + extra_expenses
            distribution = income - expenses
            mortgage = by_month[month]
            writer.writerow({
                "month": f"{YEAR}-{month:02d}",
                "rental_income": usd(income),
                "operating_expenses": usd(expenses),
                "owner_distributions": usd(distribution),
                "mortgage_payment": usd(mortgage.total),
                "principal_paid": usd(-mortgage.principal),
                "interest_paid": usd(mortgage.interest),
                "escrow_contribution": usd(mortgage.escrow),
                "actual_cash_flow": usd(distribution-mortgage.total),
            })
    return result


if __name__ == "__main__":
    outputs = [build_owner_pdf(month) for month in MONTHS]
    outputs.append(build_mortgage_pdf())
    outputs.append(build_expected_totals())
    for path in outputs:
        print(path.name)
