class DbIdConverter:
    """URL ids: 1-9 digits only, so a huge number can never reach the database (it gives a clean 404)."""

    regex = "[0-9]{1,9}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return str(value)
