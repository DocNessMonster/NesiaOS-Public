class Property:
	"""Represent a residential rental property."""

	def __init__(
		self,
		name,
		address,
		purchase_price,
		current_value,
		mortgage_balance,
		interest_rate,
		monthly_rent,
		monthly_mortgage_payment,
		annual_taxes,
		annual_insurance,
		monthly_property_management=0,
	):
		self.name = name
		self.address = address
		self.purchase_price = purchase_price
		self.current_value = current_value
		self.mortgage_balance = mortgage_balance
		self.interest_rate = interest_rate
		self.monthly_rent = monthly_rent
		self.monthly_mortgage_payment = monthly_mortgage_payment
		self.annual_taxes = annual_taxes
		self.annual_insurance = annual_insurance
		self.monthly_property_management = monthly_property_management

	@property
	def equity(self):
		"""Return current estimated property equity."""
		return self.current_value - self.mortgage_balance

	@property
	def base_monthly_cashflow(self):
		"""Return monthly cash flow before irregular expenses."""
		return (
			self.monthly_rent
			- self.monthly_mortgage_payment
			- self.monthly_property_management
		)
