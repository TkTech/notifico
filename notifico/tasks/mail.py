from celery import shared_task
from flask_mail import Message

from notifico import create_app, mail


@shared_task
def send_mail(*args, **kwargs):
    """
    Sends an email using Flask-Mail and Notifico's configuration
    settings.
    """
    # TODO: Allow bulk sending using flask.mail.Connection.
    celery_app = create_app()
    with celery_app.app_context():
        m = Message(*args, **kwargs)
        mail.send(m)
