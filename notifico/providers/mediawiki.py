from flask_babel import lazy_gettext as _

from wtforms import fields, validators

from notifico.provider import PollingProvider, ProviderForm


class MediaWikiProviderForm(ProviderForm):
    url = fields.URLField(
        _('URL'),
        validators=[
            validators.DataRequired(),
            # This is the default, but be explicit.
            validators.URL(require_tld=True)
        ],
        description=_(
            'The URL of the MediaWiki installation you want to watch for'
            ' changes.'
        )
    )

    # This is not a very user-friendly option, since even finding the IDs
    # can be tricky for a non-technical user. Can we do better, and query
    # the URL entered first to provide options? Something to revisit.
    namespace = fields.IntegerField(
        _('Namespace'),
        description=_(
            'A numerical namespace ID. Leave this blank to use the default'
            ' namespace, which is "0", and contains the main articles on most'
            ' sites.'
        )
    )


class MediaWikiProvider(PollingProvider):
    PROVIDER_NAME = 'MediaWiki'
    PROVIDER_ID = 30
    PROVIDER_DESCRIPTION = _(
        'Periodically checks a MediaWiki site for changes.'
    )

    @classmethod
    def form(cls):
        return MediaWikiProviderForm()

    @staticmethod
    def icon():
        return 'fab fa-wikipedia-w'
