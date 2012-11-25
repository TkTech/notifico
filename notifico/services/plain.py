# -*- coding: utf8 -*-
from notifico.services.service import Service


class PlainTextService(Service):
    """
    Simple service hook that just accepts text.
    """
    @staticmethod
    def service_id():
        return 20

    @staticmethod
    def service_name():
        return 'Plain Text'

    @staticmethod
    def service_url():
        return None

    @staticmethod
    def handle_request(user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            p = request.args.get('payload', None)
        if not p:
            return

        yield dict(
            type='message',
            payload=dict(
                msg=p,
                type=Service.RAW
            )
        )

