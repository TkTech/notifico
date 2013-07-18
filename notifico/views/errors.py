#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""errors.py
"""
__all__ = (
    'error_500'
)
from flask import render_template


def error_500(error):
    """
    Called when an internel server error (500) occured when
    responding to a request.
    """
    return render_template(
        'errors/500.html',
        error_code=500,
        e=error
    ), 500
