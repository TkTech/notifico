import secrets
from pathlib import Path

import pydantic
from redis import Redis
from flask import Flask
from werkzeug.middleware.shared_data import SharedDataMiddleware

from notifico.util import pretty
from notifico.authorization import has_permission
from notifico.extensions import (
    db,
    cache,
    mail,
    csrf,
    babel,
    migrate,
    login_manager
)

login_manager.login_view = 'users.login'


def _sql_default():
    path = Path.cwd() / 'testing.db'
    return f'sqlite:///{path!s}'


class Settings(pydantic.BaseSettings):
    """
    Default application settings, which can be overwritten using NOTI_
    prefixed environment variables or a .env file.
    """
    #: A Redis instance, used for caching and background workers.
    REDIS: pydantic.RedisDsn = 'redis://localhost:6379/0'
    #: Secret key used for encrypting and signing.
    SECRET_KEY: str = pydantic.Field(
        # Randomize the secret on each launch if the user hasn't provided
        # a real secret key.
        default_factory=lambda: secrets.token_hex(24)
    )
    #: Enable CSRF on all POST endpoints by default.
    # This is provided by the Flask-WTF extension.
    CSRF_ENABLED: bool = True
    #: Database DSN.
    SQLALCHEMY_DATABASE_URI: str = pydantic.Field(
        default_factory=_sql_default
    )
    # A deprecated Flask-SQLAlchemy feature, ignore this.
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    class Config:
        env_prefix = 'NOTI_'
        env_file = '.env'


@login_manager.user_loader
def user_loader(user_id):
    from notifico.models.user import User

    try:
        user_id = int(user_id)
    except ValueError:
        return

    return User.query.get(user_id)


def default_context():
    """Context variables loaded into every template by default."""
    return {'has_permission': has_permission}


def create_app():
    """
    Construct a new Notifico/Flask application instance and return it.
    """
    import os

    app = Flask(__name__)
    app.config.update(Settings().dict())

    # We want translations as early as possible, since we'll ideally use them
    # even for startup errors.
    babel.init_app(app)

    # In production, nginx should serve the static directory directly.
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/': os.path.join(os.path.dirname(__file__), 'static')
    })

    app.redis = Redis.from_url(str(app.config['REDIS']))

    cache.init_app(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_HOST': app.redis,
        'CACHE_OPTIONS': {
            'key_prefix': 'cache_'
        }
    })

    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Custom URL converters for convienience.
    from notifico.converters import (
        UserConverter,
        ProjectConverter
    )

    app.url_map.converters.update({
        'user': UserConverter,
        'project': ProjectConverter
    })

    # Import and register all of our blueprints.
    from notifico.views import (
        public,
        users,
        projects,
        webhooks,
        admin
    )

    app.register_blueprint(admin.admin, url_prefix='/a')
    app.register_blueprint(users.users, url_prefix='/u')
    app.register_blueprint(webhooks.webhooks, url_prefix='/h')
    app.register_blueprint(projects.projects)
    app.register_blueprint(public.public)

    # Setup custom Jinja2 filters.
    app.jinja_env.filters.update({
        'pretty_date': pretty.pretty_date,
        'plural': pretty.plural,
        'fix_link': pretty.fix_link
    })

    # And some custom context variables.
    app.context_processor(default_context)

    # Get all plugins that were enabled at the time the application was
    # created.
    from notifico.models.plugin import Plugin as PluginModel
    try:
        with app.app_context():
            plugins = db.session.query(PluginModel).filter(
                PluginModel.enabled.is_(True)
            ).all()
    except Exception:
        # If the database doesn't exist or hasn't been migrated, we don't
        # want to do anything at all. Bit of a chicken-and-egg scenario.
        return app

    channels = []
    for plugin in plugins:
        for blueprint in plugin.impl.register_blueprints():
            app.register_blueprint(blueprint)

        channel = plugin.impl.register_channel()
        if channel is not None:
            channels.append(channel)

    # Chuck the plugins and channels somewhere where they won't be trampled
    # or trample themselves.
    app.noti = type('Noti', (object,), {})()
    app.noti.plugins = {p.plugin_id: p for p in plugins}
    app.noti.channels = frozenset(channels)

    return app
