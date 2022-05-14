import json
from hashlib import sha256

import flask_wtf as wtf
from wtforms import fields, validators

from notifico.services.hooks import HookService
from notifico.services.hooks.github import GithubHook


class TravisConfigForm(wtf.FlaskForm):
    gh_user = fields.StringField('GitHub username', validators=[
        validators.Length(max=40)
    ], description=(
        'Case-sensitive GitHub username of repository owner.'
    ))
    repo_name = fields.StringField('Repo name', validators=[
        validators.Length(max=100)
    ], description=(
        'Case-sensitive name of repository.'
    ))
    token = fields.StringField('Travis Token', validators=[
        validators.Length(max=1024)
    ], description=(
        'Used to authenticate incoming webhooks.<br>'
        'Can be found on your '
        '<a href="https://travis-ci.org/profile/">Travis CI profile page</a>.'
    ))
    use_colors = fields.BooleanField('Use Colors', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, commit messages will include minor mIRC coloring.'
    ))


class TravisHook(HookService):
    """
    HookService hook for https://travis-ci.org.
    """
    SERVICE_NAME = 'Travis CI'
    SERVICE_ID = 60

    @classmethod
    def service_description(cls):
        return cls.env().get_template('travisci_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        payload = request.form.get('payload')
        if not payload:
            return

        payload = json.loads(payload)
        user = hook.config.get('gh_user')
        repo = hook.config.get('repo_name')
        token = hook.config.get('token')
        strip = not hook.config.get('use_colors', True)

        # http://about.travis-ci.org/docs/user/notifications/#Authorization
        auth_header = request.headers.get('Authorization')
        auth_line = '{0}/{1}{2}'.format(user, repo, token)
        auth = sha256(auth_line).hexdigest()

        # Ensure the hook is from the correct project
        if auth != auth_header:
            return

        # Check to make sure this isn't an on_start hook
        if payload['finished_at'] is None:
            return

        summary = cls._create_summary(payload)
        details = 'Details: {0}'.format(payload['build_url'])
        details = cls._prefix_line(details, payload)

        yield cls.message(summary, strip)
        yield cls.message(details, strip)

    @classmethod
    def _prefix_line(cls, line, payload):
        """
        Prefixes lines with [RepoName] and adds colours
        """

        prefix = u'{RESET}[{BLUE}{name}{RESET}] '.format(
            name=payload['repository']['name'],
            **HookService.colors
        )
        return prefix + line

    @classmethod
    def _create_summary(cls, payload):
        """
        Create and return a one-line summary of the build
        """
        status_colour = HookService.colors['RED']
        if payload['result'] == 0:
            status_colour = HookService.colors['GREEN']

        lines = []

        # Build number
        lines.append(u'Travis CI - build #{number}'.format(
            number=payload['number'],
        ))

        # Status and correct colours
        lines.append(u'{status}{message}{RESET}.'.format(
            status=status_colour,
            message=payload['result_message'].lower(),
            **HookService.colors
        ))

        # branch & commit hash
        lines.append(u'({G}{branch}{R} @ {G}{commit}{R})'.format(
            branch=payload['branch'],
            commit=payload['commit'][:7],
            G=HookService.colors['GREEN'],
            R=HookService.colors['RESET']
        ))

        # Short URL to changes on GH
        lines.append(u'{PINK}{url}{RESET}'.format(
            url=GithubHook.shorten(payload['compare_url']),
            **HookService.colors
        ))

        line = u' '.join(lines)
        return cls._prefix_line(line, payload)

    @classmethod
    def form(cls):
        return TravisConfigForm
