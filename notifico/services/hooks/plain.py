# -*- coding: utf8 -*-
__all__ = ('PlainTextHook',)
from flask.ext import wtf

from notifico.services.hooks import HookService


class PlainTextConfigForm(wtf.Form):
    use_colors = wtf.BooleanField('Use Colors', validators=[
        wtf.Optional()
    ], default=False, description=(
        'If checked, messages will include mIRC colouring.'
    ))


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
        config = hook.config or {}

        p = request.form.get('payload', None)
        if not p:
            p = request.args.get('payload', None)
            if not p:
                return

        yield cls.message(p[:512], strip=not config.get('use_colours', False))

    @classmethod
    def form(cls):
        return PlainTextConfigForm
