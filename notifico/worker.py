#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility kludge to start celery within a Flask application
context, so we can use Flask's configuration for everything.
"""
from notifico import create_instance, celery

if __name__ == '__main__':
    app = create_instance()
    with app.app_context():
        celery.start()
