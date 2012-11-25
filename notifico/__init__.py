# -*- coding: utf8 -*-
import re
from functools import wraps
from collections import deque

from flask import (
    Flask,
    g,
    redirect,
    url_for,
    session
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

app.register_blueprint(account, url_prefix='/u')
app.register_blueprint(projects, url_prefix='/p')
app.register_blueprint(public)
app.register_blueprint(pimport, url_prefix='/i')


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


@app.template_filter('fixlink')
def fix_link(s):
    if not re.match(r'^https?://', s):
        s = 'http://{0}'.format(s)
    return s


@app.before_request
def set_crumbs():
    g.add_breadcrumb = add_breadcrumb
    g.crumbs = session.get('crumbs')


def add_breadcrumb(title, link):
    crumbs = session.setdefault('crumbs', deque(maxlen=5))
    if crumbs:
        last_title, _ = crumbs[-1]
        if last_title == title:
            return
    crumbs.append((title, link))


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
        import logging
        file_handler = logging.FileHandler('notifico.log')
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

    # Let SQLAlchemy create any missing tables.
    db.create_all()

    return app
