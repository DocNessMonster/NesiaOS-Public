"""Side-effect-free US residential rental depreciation scenario calculations.

This models common 27.5-year straight-line, mid-month *estimates* for a former
personal residence and a subsequent qualifying building improvement. It is
not a tax preparation system, tax-basis determination, or filed-return import.
FMV and adjusted acquisition basis must be independently substantiated.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CENT = Decimal("0.01")
YEARS = Decimal("27.5")


def amount(value):
    """Accept only finite, nonnegative monetary amounts."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Amounts must be finite numbers") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Amounts must be finite and nonnegative")
    return result


def percent(value):
    value = amount(value)
    if value > 100:
        raise ValueError("Building allocation must be between 0 and 100 percent")
    return value / 100


def rounded(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def mid_month_fraction(placed_in_service, year):
    """Time share under 27.5-year residential rental mid-month convention.

    This is intended for years 1 and 2, not a complete 27.5-year
    disposition schedule.
    """
    if not isinstance(placed_in_service, date):
        raise ValueError("A placed-in-service date is required")
    if year < placed_in_service.year:
        return Decimal(0)
    if year == placed_in_service.year:
        return (Decimal(12 - placed_in_service.month) + Decimal("0.5")) / 12
    # Full years following the placement year; later years require an
    # end-of-recovery-period calculation, not this simple helper.
    if year < placed_in_service.year + 27:
        return Decimal(1)
    raise ValueError("Later recovery-period years require a full MACRS schedule")


@dataclass(frozen=True)
class RentalDepreciationScenario:
    acquisition_price: object
    acquisition_closing_costs: object
    acquisition_building_pct: object
    pre_rental_improvements: object
    conversion_fmv: object
    conversion_building_pct: object
    original_placed_in_service: date
    improvement_cost: object = 0
    improvement_placed_in_service: date | None = None

    def calculate(self, year):
        year = int(year)
        if not 2000 <= year <= 2100:
            raise ValueError("Invalid tax year")
        purchase = amount(self.acquisition_price)
        closings = amount(self.acquisition_closing_costs)
        improvements = amount(self.pre_rental_improvements)
        fmv = amount(self.conversion_fmv)
        base_share = percent(self.acquisition_building_pct)
        fmv_share = percent(self.conversion_building_pct)
        if purchase <= 0 or fmv <= 0 or base_share <= 0 or fmv_share <= 0:
            raise ValueError("Purchase price, conversion FMV, and building allocations must be positive")
        if not isinstance(self.original_placed_in_service, date):
            raise ValueError("Original rental availability date is required")
        new_cost = amount(self.improvement_cost)
        if new_cost and not isinstance(self.improvement_placed_in_service, date):
            raise ValueError("Improvement date is required for nonzero improvement cost")

        original_building_cost = (purchase + closings) * base_share
        adjusted_building_basis = original_building_cost + improvements
        fmv_building = fmv * fmv_share
        depreciable_house_basis = min(adjusted_building_basis, fmv_building)
        limiting_basis = "adjusted_cost" if adjusted_building_basis <= fmv_building else "conversion_fmv"
        house_share = mid_month_fraction(self.original_placed_in_service, year)
        house_depreciation = rounded(depreciable_house_basis / YEARS * house_share)

        new_share = (mid_month_fraction(self.improvement_placed_in_service, year)
                     if new_cost else Decimal(0))
        new_depreciation = rounded(new_cost / YEARS * new_share)
        return {
            "year": year,
            "original_building_cost": rounded(original_building_cost),
            "adjusted_building_basis": rounded(adjusted_building_basis),
            "conversion_fmv_building": rounded(fmv_building),
            "depreciable_house_basis": rounded(depreciable_house_basis),
            "limiting_basis": limiting_basis,
            "house_depreciation": house_depreciation,
            "improvement_depreciation": new_depreciation,
            "total_depreciation": house_depreciation + new_depreciation,
            "verified": False,
        }
