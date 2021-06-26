from flask import Request
from flask_babel import lazy_gettext as _

from notifico import errors
from notifico.provider import WebhookProvider


class PlainProvider(WebhookProvider):
    PROVIDER_NAME = 'Plain Text'
    PROVIDER_ID = 10
    PROVIDER_DESCRIPTION = _(
        'An extremely basic webhook that accepts one argument, "payload".'
        ' Good for simple embedded devices and shell scripts.'
    )

    @classmethod
    def pack_payload(cls, provider, request: Request):
        if request.method == 'POST':
            try:
                msg = request.form['payload']
            except KeyError:
                raise errors.PayloadNotValidError()

            return msg

        # No need for a size check, we globally don't allow URLs that large.
        try:
            msg = request.args['payload']
        except KeyError:
            raise errors.PayloadNotValidError()

        return msg

    @classmethod
    def handle_request(cls, provider, payload):
        pass
