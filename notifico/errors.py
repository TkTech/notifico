class PayloadError(ValueError):
    pass


class ProviderError(ValueError):
    def __init__(self, msg=None, *, payload=None):
        super().__init__(msg)
        self.payload = payload


class PayloadNotValidError(PayloadError):
    """Raised when a webhook payload does not match what was expected."""
