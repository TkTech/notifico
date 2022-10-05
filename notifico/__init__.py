from functools import wraps

from redis import Redis
from celery import Celery
from flask import (
    Flask,
    g,
    redirect,
    url_for
)
from flask_caching import Cache
from flask_mail import Mail
from raven.contrib.flask import Sentry
from werkzeug.middleware.proxy_fix import ProxyFix

from notifico.database import db_session
from notifico.settings import Settings
from notifico.util import pretty

sentry = Sentry()
cache = Cache()
mail = Mail()
celery = Celery()


def user_required(f):
    """
    A decorator for views which required a logged-in user.
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


def create_app():
    """
    Construct a new Flask instance and return it.
    """

    app = Flask(__name__)
    # app.config.from_object('notifico.config')
    app.config.from_mapping(Settings().dict())

    if app.config.get('SENTRY_DSN'):
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=app.config['SENTRY_DSN'],
            integrations=[
                FlaskIntegration()
            ]
        )

    if app.config.get('ROUTE_STATIC'):
        # We should handle routing for static assets ourself (handy for
        # small and quick deployments).
        import os.path
        from werkzeug.middleware.shared_data import SharedDataMiddleware

        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/': os.path.join(os.path.dirname(__file__), 'static')
        })

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    # Setup our redis connection (which is already thread safe)
    app.redis = Redis.from_url(app.config['REDIS'])
    cache.init_app(app)
    mail.init_app(app)

    # Update celery's configuration with our application config.
    celery.config_from_object(app.config)

    # Import and register all of our blueprints.
    from notifico.views import account
    from notifico.views import public
    from notifico.views import projects

    app.register_blueprint(account.account, url_prefix='/u')
    app.register_blueprint(projects.projects)
    app.register_blueprint(public.public)

    # Register our custom error handlers.
    from notifico.views import errors

    app.register_error_handler(500, errors.error_500)

    # Setup some custom Jinja2 filters.
    app.jinja_env.filters['pretty_date'] = pretty.pretty_date
    app.jinja_env.filters['plural'] = pretty.plural
    app.jinja_env.filters['fix_link'] = pretty.fix_link

    if app.config['USE_PROXY_HEADERS']:
        count = app.config['USE_PROXY_HEADERS']
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=count, x_proto=count)

    return app
