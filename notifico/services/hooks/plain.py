# -*- coding: utf8 -*-
__all__ = ('PlainTextHook',)

from notifico.services.hooks import HookService


class PlainTextHook(HookService):
    """
    Simple service hook that just accepts text.
    """
    SERVICE_ID = 20
    SERVICE_NAME = 'Plain Text'

    @classmethod
    def service_description(cls):
        return cls.env().get_template('plain_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            p = request.args.get('payload', None)
            if not p:
                return
        yield cls.message(p[:512])
