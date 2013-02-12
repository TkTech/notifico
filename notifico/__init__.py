# -*- coding: utf8 -*-
import re
from functools import wraps
from datetime import datetime

import redis
from flask import (
    Flask,
    g,
    redirect,
    url_for
)
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.gravatar import Gravatar

app = Flask(__name__)
db = SQLAlchemy(app)
gravatar = Gravatar(
    app,
    size=100,
    rating='g',
    default='retro',
    force_default=False,
    force_lower=False
)


def user_required(f):
    """
    A decorator for views which required a logged in user.
    """
    @wraps(f)
    def _wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('account.login'))
        return f(*args, **kwargs)
    return _wrapped

from notifico.views.account import account
from notifico.views.public import public
from notifico.views.projects import projects
from notifico.views.pimport import pimport
from notifico.views.admin import admin

app.register_blueprint(account, url_prefix='/u')
app.register_blueprint(projects)
app.register_blueprint(public)
app.register_blueprint(pimport, url_prefix='/i')
app.register_blueprint(admin, url_prefix='/_')


@app.context_processor
def installation_variables():
    """
    Include static template variables from the configuration file in
    every outgoing template. Typically used for branding.
    """
    return app.config['TEMP_VARS']


@app.before_request
def set_db():
    g.db = db
    g.redis = redis.StrictRedis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB']
    )


@app.template_filter('fixlink')
def fix_link(s):
    """
    If the string `s` (which is a link) does not begin with http or https,
    append http and return it.
    """
    if not re.match(r'^https?://', s):
        s = 'http://{0}'.format(s)
    return s


@app.template_filter('pretty')
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.now()
    diff = now - time
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"


def start(debug=False):
    """
    Sets up a basic deployment ready to run in production in light usage.

    Ex: ``gunicorn -w 4 -b 127.0.0.1:4000 "notifico:start()"``
    """
    import os
    import os.path
    from werkzeug import SharedDataMiddleware

    app.config.from_object('notifico.default_config')

    if app.config.get('HANDLE_STATIC'):
        # We should handle routing for static assets ourself (handy for
        # small and quick deployments).
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/': os.path.join(os.path.dirname(__file__), 'static')
        })

    if debug:
        # Override the configuration's DEBUG setting.
        app.config['DEBUG'] = True

    if not app.debug:
        # If the app is not running with the built-in debugger, log
        # exceptions to a file.
        import logging
        file_handler = logging.FileHandler('notifico.log')
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

    # Let SQLAlchemy create any missing tables.
    db.create_all()

    return app
