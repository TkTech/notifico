from flask import Request
from flask_babel import lazy_gettext as _

from notifico import errors
from notifico.plugin import WebhookSource


class PlainSource(WebhookSource):
    SOURCE_NAME = 'Plain Text'
    SOURCE_ID = 10
    SOURCE_DESCRIPTION = _(
        'An extremely basic webhook that accepts one argument, "payload".'
        ' Good for simple embedded devices and shell scripts.'
    )

    @classmethod
    def pack_payload(cls, source, request: Request):
        if request.method == 'POST':
            try:
                msg = request.form['payload']
            except KeyError:
                raise errors.PayloadNotValidError()

            return msg

        try:
            msg = request.args['payload']
        except KeyError:
            raise errors.PayloadNotValidError()

        return msg

    @classmethod
    def handle_request(cls, source, payload):
        pass
