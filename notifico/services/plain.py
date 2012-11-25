# -*- coding: utf8 -*-
from notifico.services.service import Service


class PlainTextService(Service):
    """
    Simple service hook that just accepts text.
    """
    SERVICE_ID = 20
    SERVICE_NAME = 'Plain Text'

    @staticmethod
    def service_description():
        return PlainTextService.env().get_template('plain_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            p = request.args.get('payload', None)
            if not p:
                return
        yield cls.message(p[:512], type_='raw')
