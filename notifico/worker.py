#!/usr/bin/env python
"""
Utility kludge to start celery within a Flask application
context, so we can use Flask's configuration for everything.
"""
from notifico import create_app, celery

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        celery.start()
