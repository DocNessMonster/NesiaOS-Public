"""Capital improvements ledger; private data stays in local_data/."""
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAPITAL_DB = ROOT / "local_data/capital/capital.sqlite"
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS capital_improvements (
 asset_id TEXT PRIMARY KEY,
 description TEXT NOT NULL,
 cost_cents INTEGER NOT NULL,
 completion_date TEXT NOT NULL,
 placed_in_service_date TEXT,
 payment_date TEXT,
 payment_source TEXT,
 asset_type TEXT,
 tax_treatment_status TEXT,
 notes TEXT
)
"""


def list_improvements(db_path=None):
    """Read capital improvements without creating a database."""
    path = Path(db_path or DEFAULT_CAPITAL_DB).expanduser()
    if not path.is_file():
        return []
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(
            "SELECT * FROM capital_improvements ORDER BY completion_date, asset_id"
        )]


def add_improvement(asset_id, description, cost, completion_date,
                    payment_source="owner_direct", placed_in_service_date=None,
                    payment_date=None, asset_type="other", notes="", db_path=None):
    """Add one capital asset, rejecting duplicate IDs."""
    amount = Decimal(str(cost))
    cents = amount * 100
    if not amount.is_finite() or amount <= 0 or cents != cents.to_integral_value():
        raise ValueError("Cost must be positive with at most two decimals")
    for value in (completion_date, placed_in_service_date, payment_date):
        if value is not None and date.fromisoformat(value).isoformat() != value:
            raise ValueError("Dates must use YYYY-MM-DD")
    if not asset_id.strip() or not description.strip():
        raise ValueError("Asset ID and description are required")
    path = Path(db_path or DEFAULT_CAPITAL_DB).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(CREATE_TABLE)
        if conn.execute(
            "SELECT 1 FROM capital_improvements WHERE asset_id=?", (asset_id,)
        ).fetchone():
            raise ValueError(f"Asset ID already exists: {asset_id}")
        conn.execute(
            "INSERT INTO capital_improvements VALUES (?,?,?,?,?,?,?,?,?,?)",
            (asset_id, description, int(cents), completion_date,
             placed_in_service_date, payment_date, payment_source, asset_type,
             "pending_review", notes),
        )
