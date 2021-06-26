from celery import Celery

from notifico.app import create_app


def make_celery():
    """
    Constructs a Celery instance with a default Task that will always have
    a Flask application context available to it.
    """
    app = create_app()
    celery = Celery()

    celery.config_from_object(app.config['CELERY'])

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery()

# Do not depend on celery's normal automatic discovery, as we may never
# import the modules with tasks in them. Always list any file that contains
# a task below.
celery.autodiscover_tasks([
    'notifico.tasks.webhooks'
], force=True)
