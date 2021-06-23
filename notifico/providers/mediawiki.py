from flask_babel import lazy_gettext as _

from notifico.provider import PollingProvider


class MediaWikiProvider(PollingProvider):
    PROVIDER_NAME = 'MediaWiki'
    PROVIDER_ID = 30
    PROVIDER_DESCRIPTION = _(
        'Periodically checks a MediaWiki site for changes.'
    )

    @staticmethod
    def icon():
        return 'fab fa-wikipedia-w'
