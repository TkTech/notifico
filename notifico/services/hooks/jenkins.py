# -*- coding: utf8 -*-
__all__ = ('JenkinsHook',)

import json

from flask.ext import wtf

from notifico.services.hooks import HookService


class JenkinsConfigForm(wtf.Form):
    phase = wtf.SelectMultipleField('Phase',
        default=['finished'],
        choices=[
            ('started', 'Started'),
            ('completed', 'Completed'),
            ('finished', 'Finished')
        ],
        description=(
            'Print messages for selected fields.'
    ))

    status = wtf.SelectMultipleField('Status',
        default=['success', 'unstable', 'failure'],
        choices=[
            ('success', 'Success'),
            ('unstable', 'Unstable'),
            ('failure', 'Failure')
        ],
        description=(
            'Print messages for selected fields.'
    ))

    use_colors = wtf.BooleanField('Use Colors', validators=[
        wtf.Optional()
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
        if not phase in hook.config.get('phase', []):
            return

        status = payload['build'].get('status', 'SUCCESS').lower()
        # yeah documentation of the plugin differs
        # from the actual implementation?
        if status == 'failed':
            status = 'failure'
        if not status in hook.config.get('status', []):
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
            name=payload['name'],
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
            'FAILURE' : HookService.colors['RED'],
            'FAILED': HookService.colors['RED']
        }.get(
            payload['build'].get('status', 'SUCCESS'),
            HookService.colors['RED']
        )

        number = payload['build']['number']
        phase = payload['build']['phase'].lower()
        status = payload['build']['status'].lower()
        url = payload['build']['full_url']

        fmt_string = (
            '{ORANGE}jenkins{RESET} built {status_colour}#{number}{RESET} '
            '{phase} ({status_colour}{status}{RESET}) {PINK}{url}{RESET}'
        )

        line = fmt_string.format(
            status_colour=status_colour,
            number=number,
            phase=phase,
            status=status,
            url=url,
            **HookService.colors
        )
        return cls._prefix_line(line, payload)

    @classmethod
    def form(cls):
        return JenkinsConfigForm
