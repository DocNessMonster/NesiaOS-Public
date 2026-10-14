
from decimal import Decimal
from pathlib import Path

from src.services.appfolio_importer import parse_pdf


SAMPLE_PDF = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "sample_owner_statement.pdf"
)


def test_import_transactions():
    """Check transaction counts and financial totals."""

    rows, totals = parse_pdf(SAMPLE_PDF)

    assert len(rows) == 4
    assert totals["income"] == Decimal("2000.00")
    assert totals["expense"] == Decimal("2000.00")
    assert totals["closing"] == Decimal("500.00")


def test_transaction_categories():
    """Check transaction classifications."""

    rows, _ = parse_pdf(SAMPLE_PDF)
    categories = {row["category"] for row in rows}

    assert "rent_income" in categories
    assert "management_fee" in categories
    assert "plumbing" in categories
    assert "owner_distribution" in categories


def test_owner_draw_is_transfer():
    """Owner distributions are transfers, not operating expenses."""

    rows, _ = parse_pdf(SAMPLE_PDF)

    owner_draws = [
        row for row in rows
        if row["category"] == "owner_distribution"
    ]

    assert len(owner_draws) == 1
    assert owner_draws[0]["flow_type"] == "transfer"
    assert Decimal(owner_draws[0]["expense"]) == Decimal("1675.00")
