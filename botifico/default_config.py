# ---
# Default Botifico Configuration
# ---

# ---
# Redis Configuration
# ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

SQLALCHEMY_DATABASE_URI = 'sqlite:///testing.db'

try:
    from local_config import *
except ImportError:
    pass
