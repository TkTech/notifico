from celery import Celery

from notifico import create_app
from notifico.settings import Settings


def make_celery():
    app = create_app()
    settings = Settings()

    celery_instance = Celery(
        app.import_name,
        backend=settings.REDIS,
        broker=settings.REDIS,
    )
    celery_instance.config_from_object(settings, namespace='celery_')

    class ContextTask(celery_instance.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_instance.Task = ContextTask  # noqa
    return celery_instance


celery = make_celery()
