# ---
# Default Notifico Configuration
# ---
import os

# ---
# Flask Misc.
# ---
SECRET_KEY = 'YouReallyShouldChangeThisYouKnow'

# ---
# Flask-SQLAlchemy
# ---
db_path = os.path.abspath(os.path.join(os.getcwd(), 'testing.db'))
SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(db_path)

# ---
# Flask-WTF
# ---
CSRF_ENABLED = True

# ---
# Redis Configuration
# ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# ---
# Service integration configuration.
# ---
SERVICE_GITHUB_CLIENT_ID = None
SERVICE_GITHUB_CLIENT_SECRET = None

GOOGLE = None

# ---
# Misc. Settings
# ---
# Should Notifico route static assets (/css/, /js/, etc...)?
HANDLE_STATIC = True

# Usually-static variables injected into each template. Useful
# for branding for internal use.
TEMP_VARS = {
    'site_title': 'Notifico',
    'site_label': 'Notifico'
}

# Should new users be allowed to register?
PUBLIC_NEW_USERS = True

try:
    from local_config import *
except ImportError:
    pass
