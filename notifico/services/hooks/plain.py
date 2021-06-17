# -*- coding: utf8 -*-
__all__ = ('PlainTextHook',)
import flask_wtf as wtf
from wtforms import fields, validators

from notifico.services.hooks import HookService


class PlainTextConfigForm(wtf.FlaskForm):
    use_colours = fields.BooleanField('Use Colors', validators=[
        validators.Optional()
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

        for line in p.splitlines():
            yield cls.message(
                # FIXME: Hard-cap each line to 512 characters.
                #        This needs to be done intelligently, likely
                #        by the bot itself.
                line[:512],
                strip=not config.get('use_colours', False)
            )

    @classmethod
    def form(cls):
        return PlainTextConfigForm
