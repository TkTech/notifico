# -*- coding: utf-8 -*-
from flask_mail import Message

from notifico import create_instance, celery, mail


@celery.task
def send_mail(*args, **kwargs):
    """
    Sends an email using Flask-Mail and Notifico's configuration
    settings.
    """
    # TODO: Allow bulk sending using flask.mail.Connection.
    celery_app = create_instance()
    with celery_app.app_context():
        m = Message(*args, **kwargs)
        mail.send(m)
