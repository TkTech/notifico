# ---
# Default Botifico Configuration
# ---
import os

# ---
# Redis Configuration
# ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

try:
    from local_config import *
except ImportError:
    pass
