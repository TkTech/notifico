from flask import render_template
from werkzeug.http import HTTP_STATUS_CODES


def generic_error(error, *, error_code=500):
    """
    Called when an internal server error occurred during a request.
    """
    return render_template(
        'errors/generic.html',
        error_code=error_code,
        error_message=HTTP_STATUS_CODES.get(error_code),
        e=error
    ), error_code
