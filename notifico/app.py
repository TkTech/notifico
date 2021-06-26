from redis import Redis
from flask import Flask
from werkzeug.middleware.shared_data import SharedDataMiddleware

from notifico.util import pretty
from notifico.extensions import (
    db,
    cache,
    mail,
    babel,
    migrate,
    login_manager
)


def user_loader(user_id):
    from notifico.models.user import User

    try:
        user_id = int(user_id)
    except ValueError:
        return

    return User.query.get(user_id)


def create_app():
    """
    Construct a new Flask instance and return it.
    """
    import os

    app = Flask(__name__)
    app.config.from_object('notifico.config')
    app.config.from_envvar('NOTIFICO_CONFIG', silent=True)

    # We want translations as early as possible, since we'll ideally use them
    # even for startup errors.
    babel.init_app(app)

    # We should handle routing for static assets ourself (handy for small and
    # quick deployments).
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

    login_manager.login_view = 'users.login'
    login_manager.user_loader(user_loader)
    login_manager.init_app(app)

    # Custom URL converters for convienience.
    from notifico.converters import (
        UserConverter,
        ProjectConverter
    )

    app.url_map.converters['user'] = UserConverter
    app.url_map.converters['project'] = ProjectConverter

    # Import and register all of our blueprints.
    from notifico.views import (
        public,
        users,
        projects,
        webhooks
    )

    app.register_blueprint(users.users, url_prefix='/u')
    app.register_blueprint(webhooks.webhooks, url_prefix='/h')
    app.register_blueprint(projects.projects)
    app.register_blueprint(public.public)

    # Setup some custom Jinja2 filters.
    app.jinja_env.filters['pretty_date'] = pretty.pretty_date
    app.jinja_env.filters['plural'] = pretty.plural
    app.jinja_env.filters['fix_link'] = pretty.fix_link

    return app
