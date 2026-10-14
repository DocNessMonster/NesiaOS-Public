
class Expense:
    """Represent a single property-related expense."""

    def __init__(
        self,
        date,
        amount,
        category,
        description="",
        vendor="",
        property_name="",
    ):
        self.date = date
        self.amount = amount
        self.category = category
        self.description = description
        self.vendor = vendor
        self.property_name = property_name

    @property
    def tax_year(self):
        """Return the year associated with the expense."""
        return int(self.date[:4])

    