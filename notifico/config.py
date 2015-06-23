# ---
# Default Notifico Configuration
# ---
import os

# ---
# Flask Misc.
# ---
# This key MUST be changed before you make a site public, as it is used
# to sign the secure cookies used for sessions.
SECRET_KEY = 'YouReallyShouldChangeThisYouKnow'

# ---
# Flask-SQLAlchemy
# ---
db_path = os.path.abspath(os.path.join(os.getcwd(), 'testing.db'))
SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(db_path)

# ---
# Flask-WTF
# ---
# Automatic CSRF support on forms to protect from attacks. It is
# always recommended to leave this on.
CSRF_ENABLED = True

# ---
# Flask-Mail
# ---
# Allows Notifico to send password reset emails and other
# notifications.
# MAIL_SERVER = 'localhost'
# MAIL_PORT = 25
# MAIL_USE_TLS = False
# MAIL_USE_SSL = False
# MAIL_USERNAME = None
# MAIL_PASSWORD = None
# DEFAULT_MAIL_SENDER = None

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

# Your Sentry (http://getsentry.com) DSN key.
SENTRY_DSN = None

# ---
# Celery Configuration
# ---
BROKER_URL = 'redis://'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_IMPORTS = ('notifico.services.background',)
CELERY_TASK_SERIALIZER = 'json'


# ---
# Misc. Settings
# ---

# Should Notifico route static assets (/css/, /js/, etc...)?
# This is really only useful for debugging and for small deployments.
# Larger deploys should set this to False and have their proxy/server
# handle the /static directory.
NOTIFICO_ROUTE_STATIC = True

# Should new users be allowed to register?
NOTIFICO_NEW_USERS = True

# Should notifico send password reset emails? This requires
# Flask-Mail to be properly configured.
NOTIFICO_PASSWORD_RESET = False
# How long (in seconds) password resets should be valid for.
NOTIFICO_PASSWORD_RESET_EXPIRY = 60 * 60 * 24
# The address or (name, address) to use when sending an email.
NOTIFICO_MAIL_SENDER = None

try:
    from local_config import *
except ImportError:
    pass
