from src.models.property import Property


example_property = Property(
    name="Example Rental",
    address="123 Example Street",
    purchase_price=180000,
    current_value=250000,
    mortgage_balance=120000,
    interest_rate=4.0,
    monthly_rent=1800,
    monthly_mortgage_payment=950,
    annual_taxes=2200,
    annual_insurance=1000,
    monthly_property_management=180,
)

print("Equity:", example_property.equity)
print("Base monthly cash flow:", example_property.base_monthly_cashflow)
