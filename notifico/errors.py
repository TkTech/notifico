class PayloadError(ValueError):
    pass


class PayloadNotValidError(PayloadError):
    """Raised when a webhook payload does not match what was expected."""
