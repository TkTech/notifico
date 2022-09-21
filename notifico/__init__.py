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
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from raven.contrib.flask import Sentry

from notifico.settings import Settings
from notifico.util import pretty

db = SQLAlchemy()
sentry = Sentry()
cache = Cache()
mail = Mail()
celery = Celery()
migrate = Migrate()


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
    import os

    app = Flask(__name__)
    # app.config.from_object('notifico.config')
    app.config.from_mapping(Settings().dict())

    if app.config.get('ROUTE_STATIC'):
        # We should handle routing for static assets ourself (handy for
        # small and quick deployments).
        import os.path
        from werkzeug.middleware.shared_data import SharedDataMiddleware

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
    cache.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    # Update celery's configuration with our application config.
    celery.config_from_object(app.config)

    # Import and register all of our blueprints.
    from notifico.views.account import account
    from notifico.views.public import public
    from notifico.views.projects import projects

    app.register_blueprint(account, url_prefix='/u')
    app.register_blueprint(projects)
    app.register_blueprint(public)

    # Register our custom error handlers.
    from notifico.views import errors

    app.register_error_handler(500, errors.error_500)

    # Setup some custom Jinja2 filters.
    app.jinja_env.filters['pretty_date'] = pretty.pretty_date
    app.jinja_env.filters['plural'] = pretty.plural
    app.jinja_env.filters['fix_link'] = pretty.fix_link

    return app
