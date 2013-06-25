# -*- coding: utf8 -*-
from functools import wraps

from redis import Redis
from celery import Celery
from flask import (
    Flask,
    g,
    redirect,
    url_for
)
from flask.ext.cache import Cache
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
from raven.contrib.flask import Sentry

from notifico.util import pretty

db = SQLAlchemy()
sentry = Sentry()
cache = Cache()
mail = Mail()
celery = Celery()


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


def group_required(name):
    """
    A decorator for views which required a user to be member
    to a particular group.
    """
    def _wrap(f):
        @wraps(f)
        def _wrapped(*args, **kwargs):
            if g.user is None or not g.user.in_group(name):
                return redirect(url_for('account.login'))
            return f(*args, **kwargs)
        return _wrapped
    return _wrap


def create_instance():
    """
    Construct a new Flask instance and return it.
    """
    import os

    app = Flask(__name__)
    app.config.from_object('notifico.default_config')

    if app.config.get('NOTIFICO_ROUTE_STATIC'):
        # We should handle routing for static assets ourself (handy for
        # small and quick deployments).
        import os.path
        from werkzeug import SharedDataMiddleware

        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/': os.path.join(os.path.dirname(__file__), 'static')
        })

    if not app.debug:
        # If sentry (http://getsentry.com) is configured for
        # error collection we should use it.
        if app.config.get('SENTRY_DSN'):
            sentry.dsn = app.config.get('SENTRY_DSN')
            sentry.init_app(app)

    # Setup our redis connection (which is already thread safe)
    app.redis = Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB']
    )
    # Attach Flask-Cache to our application instance. We override
    # the backend configuration settings because we only want one
    # Redis instance.
    cache.init_app(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_HOST': app.redis,
        'CACHE_OPTIONS': {
            'key_prefix': 'cache_'
        }
    })
    # Attach Flask-Mail to our application instance.
    mail.init_app(app)
    # Attach Flask-SQLAlchemy to our application instance.
    db.init_app(app)

    # Update celery's configuration with our application config.
    celery.config_from_object(app.config)

    # Import and register all of our blueprints.
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

    # cia.vc XML-RPC kludge.
    from notifico.services.hooks.cia import handler
    handler.connect(app, '/RPC2')

    # Setup some custom Jinja2 filters.
    app.jinja_env.filters['pretty_date'] = pretty.pretty_date
    app.jinja_env.filters['plural'] = pretty.plural
    app.jinja_env.filters['fix_link'] = pretty.fix_link

    return app
