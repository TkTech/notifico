from flask_wtf import FlaskForm
from flask_babel import lazy_gettext as _
from wtforms import fields, validators

from notifico.provider import WebhookProvider


class GithubProviderForm(FlaskForm):
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


class GithubProvider(WebhookProvider):
    PROVIDER_NAME = 'Github'
    PROVIDER_ID = 20
    PROVIDER_DESCRIPTION = _(
        'Accepts all types of events from Github, such as new commits,'
        ' new Pull Requests, changed team members, etc...'
    )

    @classmethod
    def form(cls):
        return GithubProviderForm()
