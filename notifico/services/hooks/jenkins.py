# -*- coding: utf8 -*-
__all__ = ('JenkinsHook',)

import json
import urllib

import flask_wtf as wtf
from wtforms import fields, validators

from notifico.services.hooks import HookService


class JenkinsConfigForm(wtf.FlaskForm):
    phase = fields.SelectMultipleField(
        'Phase',
        default=['finalized'],
        choices=[
            ('started', 'Started'),
            ('completed', 'Completed'),
            ('finalized', 'Finalized')
        ],
        description=('Print messages for selected fields.')
    )

    status = fields.SelectMultipleField(
        'Status',
        default=['success', 'unstable', 'failure'],
        choices=[
            ('success', 'Success'),
            ('unstable', 'Unstable'),
            ('failure', 'Failure')
        ],
        description=('Print messages for selected fields.')
    )

    use_colors = fields.BooleanField('Use Colors', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, messages will include minor mIRC coloring.'
    ))


class JenkinsHook(HookService):
    """
    HookService hook for
    https://wiki.jenkins-ci.org/display/JENKINS/Notification+Plugin.
    """
    SERVICE_NAME = 'Jenkins CI'
    SERVICE_ID = 70

    @classmethod
    def service_description(cls):
        return cls.env().get_template('jenkins_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        try:
            payload = json.loads(request.data)
        except ValueError:
            return
        if not payload:
            return

        phase = payload['build']['phase'].lower()
        # finished is the the phase name of an older version
        if phase == 'finished':
            phase = 'finalized'
        if phase not in hook.config.get('phase', []):
            return

        status = payload['build'].get('status', 'SUCCESS').lower()
        # yeah documentation of the plugin differs
        # from the actual implementation?
        if status == 'failed':
            status = 'failure'
        if status not in hook.config.get('status', []):
            return

        strip = not hook.config.get('use_colors', True)
        summary = cls._create_summary(payload)

        yield cls.message(summary, strip)

    @classmethod
    def _prefix_line(cls, line, payload):
        """
        Prefixes lines with [JobName] and adds colours
        """
        prefix = u'{RESET}[{BLUE}{name}{RESET}] '.format(
            # Project names may be encoded depending on the version of
            # jekins being used.
            name=urllib.unquote(payload['name']),
            **HookService.colors
        )
        return prefix + line

    @classmethod
    def _create_summary(cls, payload):
        """
        Create and return a one-line summary of the build
        """
        status_colour = {
            'SUCCESS': HookService.colors['GREEN'],
            'UNSTABLE': HookService.colors['ORANGE'],
            # documentation differs from implementation
            'FAILURE': HookService.colors['RED'],
            'FAILED': HookService.colors['RED']
        }.get(
            payload['build'].get('status', 'SUCCESS').upper(),
            HookService.colors['RED']
        )

        number = payload['build']['number']
        phase = payload['build']['phase'].lower()
        url = payload['build']['full_url']

        status = payload['build'].get('status', '').lower()
        if status:
            # make sure this string starts with a space or
            # the formatting won't look good (see fmt_string)
            status = ': {status_colour}{status}{RESET}'.format(
                status_colour=status_colour,
                status=status,
                **HookService.colors
            )

        commit = ''
        scm = payload['build'].get('scm', {})
        if scm.get('commit'):
            # space is important again
            commit = '({GREEN}{commit}{RESET}) '.format(
                commit=scm.get('commit')[:7],
                **HookService.colors
            )

        fmt_string = (
            '{ORANGE}jenkins{RESET} build {status_colour}#{number}{RESET} '
            '{commit}{phase}{status} {PINK}{url}{RESET}'
        )

        line = fmt_string.format(
            status_colour=status_colour,
            number=number,
            commit=commit,
            phase=phase,
            status=status,
            url=url,
            **HookService.colors
        )
        return cls._prefix_line(line, payload)

    @classmethod
    def form(cls):
        return JenkinsConfigForm
