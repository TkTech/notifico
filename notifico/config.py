"""
This file contains the default configuration for Notifico.
"""
import os


# This object is passed to Celery as it's configuration. See the Celery
# documentation for more details and available options.
class CELERY:
    # Options other than Redis are not tested.
    broker_url = 'redis://'
    # Options other than Redis are not tested.
    celer_result_backend = 'redis://localhost:6379/0'
    # You should always leave this as JSON. Other options are not tested,
    # and may be unsafe.
    celery_task_serializer = 'json'


#: This key MUST be changed before you make a site public, as it is used
#: to sign the secure cookies used for sessions.
SECRET_KEY = 'YouReallyShouldChangeThisYouKnow'

db_path = os.path.abspath(os.path.join(os.getcwd(), 'testing.db'))

#: The URI for the database.
SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(db_path)

# Always leave this one as False. Tracking is a useless feature that kills
# performance.
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Automatic CSRF support on forms to protect from attacks. It is
# always recommended to leave this on.
CSRF_ENABLED = True

# Redis configuration used for the caching and locking layer. Can be the same
# as the Redis database used for Celery.
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# If the nickname is taken a random string will get appended
IRC_NICKNAME = 'Not'
IRC_USERNAME = u'notifico'
IRC_REALNAME = u"Notifico! - https://github.com/tktech"

#: [Optional] Your Sentry (http://getsentry.com) DSN key. Can be used to
#: report and collect errors.
SENTRY_DSN = None

#: Should Notifico route static assets (/css/, /js/, etc...)?
#: This is really only useful for debugging and for small deployments.
#: Larger deploys should set this to False and have their proxy/server
#: handle the /static directory.
NOTIFICO_ROUTE_STATIC = True

#: Should new users be allowed to register?
NOTIFICO_NEW_USERS = True

# Configure to allow Notifico to send password reset emails and other
# notifications by mail.

# MAIL_SERVER = 'localhost'
# MAIL_PORT = 25
# MAIL_USE_TLS = False
# MAIL_USE_SSL = False
# MAIL_USERNAME = None
# MAIL_PASSWORD = None
# DEFAULT_MAIL_SENDER = None
