from flask_babel import lazy_gettext as _

from notifico.provider import WebhookProvider


class PlainProvider(WebhookProvider):
    PROVIDER_NAME = 'Plain Text'
    PROVIDER_ID = 10
    PROVIDER_DESCRIPTION = _(
        'An extremely basic webhook that accepts one argument, "payload".'
        ' Good for simple embedded devices and shell scripts.'
    )
