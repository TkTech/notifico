class NetworkError(IOError):
    pass


class ReadExceededError(NetworkError):
    """
    Raised when too much data is being read off the pipe.
    """
