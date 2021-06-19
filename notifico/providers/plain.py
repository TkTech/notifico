from notifico.provider import WebhookProvider


class PlainProvider(WebhookProvider):
    PROVIDER_NAME = 'Plain Text'
    PROVIDER_ID = 10

    @classmethod
    def description(cls, locale):
        return {
            'en_US': (
                'An extremely basic service that accepts one argument,'
                ' `payload`.'
            )
        }.get(locale, 'en_US')

    @classmethod
    def is_our_webhook(cls, payload, request):
        # Our webhook payload is as simple as it gets.
        return len(payload) == 1 and 'payload' in payload
