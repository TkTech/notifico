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
    app.config.from_object('notifico.config')
    app.config.from_envvar('NOTIFICO_CONFIG', silent=True)

    # We want translations as early as possible, since we'll ideally use them
    # even for startup errors.
    babel.init_app(app)

    # We should handle routing for static assets ourself, which is handy for
    # development and tiny deployments. Using `static_url_path` with `Flask()`
    # doesn't work for us, since we have a wildcard route. This middleware
    # runs *before* any requests even get to Flask. We want all static assets
    # at the root to support things like favicons and .well-known.
    if app.config.get('NOTIFICO_ROUTE_STATIC'):
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/': os.path.join(os.path.dirname(__file__), 'static')
        })

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
