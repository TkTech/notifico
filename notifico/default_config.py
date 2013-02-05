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
# Your Github OAuth CLIENT_ID and CLIENT_SECRET tokens, as given
# to you when you create an application on github. If one or both of
# these are left blank, the "Import From Github" button will not appear
# on the projects page.
SERVICE_GITHUB_CLIENT_ID = None
SERVICE_GITHUB_CLIENT_SECRET = None

# Your Google Analytics ID (ID-XXXXXXX) as a string.
# If left blank, the analytics snippet will not be included in the
# base template.
GOOGLE = None

# ---
# Misc. Settings
# ---
# Should Notifico route static assets (/css/, /js/, etc...)?
# This is really only useful for debugging and for small deployments.
# Larger deploys should set this to False and have their proxy/server
# handle the /static directory.
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
