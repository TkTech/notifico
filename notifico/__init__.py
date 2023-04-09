from functools import wraps, partial

from flask_wtf import CSRFProtect
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
from flask_babel import Babel
from raven.contrib.flask import Sentry
from werkzeug.middleware.proxy_fix import ProxyFix

from notifico.database import db_session
from notifico.permissions import has_permission, Action, Permission
from notifico.settings import Settings
from notifico.util import pretty

sentry = Sentry()
cache = Cache()
mail = Mail()
celery = Celery()
babel = Babel()
csrf = CSRFProtect()


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
        # We should handle routing for static assets ourselves (handy for
        # small and quick deployments).
        import os.path
        from werkzeug.middleware.shared_data import SharedDataMiddleware

        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/': os.path.join(os.path.dirname(__file__), 'static')
        })

    @app.teardown_appcontext
    def shutdown_session(exception=None): # noqa
        db_session.remove()

    # Set up our redis connection (which is already thread safe)
    app.redis = Redis.from_url(app.config['REDIS'])
    cache.init_app(app)
    mail.init_app(app)
    babel.init_app(app)
    csrf.init_app(app)

    # Update celery's configuration with our application config.
    celery.config_from_object(app.config)

    # Import and register all of our blueprints.
    from notifico.views import account
    from notifico.views import public
    from notifico.views import projects
    from notifico.views import settings
    from notifico.views import admin
    from notifico.views import chat

    app.register_blueprint(account.account, url_prefix='/u')
    app.register_blueprint(settings.settings_view, url_prefix='/u/settings')
    app.register_blueprint(admin.admin_view, url_prefix='/a')
    app.register_blueprint(chat.chat_view, url_prefix='/c')
    app.register_blueprint(projects.projects)
    app.register_blueprint(public.public)

    # Register our custom error handlers.
    from notifico.views import errors

    app.register_error_handler(
        500,
        partial(errors.generic_error, error_code=500)
    )
    app.register_error_handler(
        403,
        partial(errors.generic_error, error_code=403)
    )
    app.register_error_handler(
        404,
        partial(errors.generic_error, error_code=404)
    )

    # Setup some custom Jinja2 filters.
    app.jinja_env.filters.update({
        'pretty_date': pretty.pretty_date,
        'plural': pretty.plural,
        'service_name': pretty.service_name
    })

    @app.context_processor
    def update_context_variables():
        # Adds some globally-available variables to templates.
        return {
            'has_permission': has_permission,
            'Action': Action,
            'Permission': Permission
        }

    if app.config['USE_PROXY_HEADERS']:
        count = app.config['USE_PROXY_HEADERS']
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=count, x_proto=count)

    return app
