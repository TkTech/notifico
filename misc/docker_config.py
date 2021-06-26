# This configuration file is used by default when using the development
# docker-compose.

# Reconfigure caching and workers to point to the service instance of redis,
# which is under the literal hostname "redis".
REDIS_HOST = "redis"


class CELERY:
    broker_url = 'redis://redis:6379'
    celer_result_backend = 'redis://redis:6379/0'
    celery_task_serializer = 'json'
