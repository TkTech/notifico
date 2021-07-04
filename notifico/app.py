from functools import partial

from redis import Redis
from flask import Flask, abort
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


def _is_plugin_enabled(plugin_id):
    """
    Called before routes added by plugins. If the plugin has been disabled,
    prevents further actions and 404s.
    """
    from notifico.models.plugin import Plugin as PluginModel

    exists = db.session.query(
        PluginModel.query.filter(
            PluginModel.plugin_id == plugin_id,
            PluginModel.enabled.is_(True)
        ).exists()
    ).scalar()

    if not exists:
        abort(404)


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

    # Flask plugins are tricky to support with runtime control. Flask doesn't
    # allow us to *un*register a blueprint, nor to sanely overwite routes. The
    # current solution is to *always* register blueprints for installed
    # extensions, and control their availability with a decorator.
    # We should revisit this, and add a way to restart all servesr and workers
    # on plugin changes, probably using a SIGHUP, instead of querying for
    # enabled plugins all the time.
    from notifico.plugins.core import all_available_plugins

    for plugin_id, plugin in all_available_plugins().items():
        try:
            blueprints = plugin.register_blueprints()
        except NotImplementedError:
            pass
        else:
            for blueprint in blueprints:
                # Hijack views to 404 if the plugin is disabled.
                # What order are these getting called in? Needs to be kept
                # in mind when plugins are adding their own before_request()
                # callbacks.
                blueprint.before_request(
                    partial(
                        _is_plugin_enabled, plugin_id
                    )
                )
                app.register_blueprint(blueprint)

    return app
