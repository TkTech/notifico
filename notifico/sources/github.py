from flask_babel import lazy_gettext as _
from wtforms import fields, validators

from notifico.plugin import WebhookSource, SourceForm


class GithubSourceForm(SourceForm):
    branches = fields.StringField(
        _('Branches'),
        validators=[
            validators.Optional(),
            validators.Length(max=1024)
        ],
        description=_(
            'A comma-separated list of branches to forward, or blank for'
            ' all branches. Ex: "main,staging".'
        )
    )


class GithubSource(WebhookSource):
    SOURCE_NAME = 'Github'
    SOURCE_ID = 20
    SOURCE_DESCRIPTION = _(
        'Accepts all types of events from Github, such as new commits,'
        ' new Pull Requests, changed team members, etc...'
    )

    @classmethod
    def form(cls):
        return GithubSourceForm()

    @staticmethod
    def icon() -> str:
        return 'fab fa-github'

    @classmethod
    def pack_payload(cls, source, request):
        return request.get_data(cache=False)

    @classmethod
    def handle_request(cls, request):
        pass
