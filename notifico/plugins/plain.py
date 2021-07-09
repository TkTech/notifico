from flask import Request
from flask_babel import lazy_gettext as _

from notifico import errors
from notifico.plugins.core import Plugin, PluginMetadata
from notifico.plugins.channel import InboundWebhookChannel


class PlainTextChannel(InboundWebhookChannel):
    CHANNEL_NAME = 'Plain Text'
    CHANNEL_DESCRIPTION = _(
        'An extremely basic webhook that accepts one argument, "payload".'
        ' Good for simple embedded devices and shell scripts.'
    )

    @classmethod
    def pack_payload(cls, instance, request: Request):
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


class PlainTextPlugin(Plugin):
    @classmethod
    def metadata(cls):
        return PluginMetadata(
            version='1.0.0',
            url='https://github.com/tktech/notifico',
            author='Tyler Kennedy',
            author_email='tk@tkte.ch',
            description=(
                'A simple webhook which accepts a single, plain text payload.'
            )
        )

    @classmethod
    def register_inbound_channel(cls):
        return PlainTextChannel
