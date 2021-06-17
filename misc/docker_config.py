# This configuration file is used by default when using the development
# docker-compose.

# Reconfigure caching and workers to point to the service instance of redis,
# which is under the literal hostname "redis".
REDIS_HOST = "redis"
BROKER_URL = 'redis://redis:6379'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
