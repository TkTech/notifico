# -*- coding: utf8 -*-
__all__ = ('JenkinsHook',)

import json

from flask.ext import wtf

from notifico.services.hooks import HookService


class JenkinsConfigForm(wtf.Form):
    print_started = wtf.BooleanField('Print Started', validators=[
        wtf.Optional()
    ], default=False, description=(
        'If checked, sends a message for every started job.'
    ))

    print_completed = wtf.BooleanField('Print Completed', validators=[
        wtf.Optional()
    ], default=False, description=(
        'If checked, sends a message for every completed job.'
    ))

    print_finished = wtf.BooleanField('Print Finished', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, sends a message for every finished job.'
    ))

    omit_phase = wtf.BooleanField('Omit Phase', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, does not add the job\'s current phase to the message. '
        'Recommended if only one of the above is checked.'
    ))

    use_colors = wtf.BooleanField('Use Colors', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, commit messages will include minor mIRC coloring.'
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

        phases = {
            'STARTED': hook.config.get('print_started', False),
            'COMPLETED': hook.config.get('print_completed', False),
            'FINISHED': hook.config.get('print_finished', True)
        }
        if not phases.get(payload['build']['phase'], False):
            return

        omit_phase = hook.config.get('omit_phase', False)
        strip = not hook.config.get('use_colors', True)
        summary = cls._create_summary(payload, omit_phase)

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
    def _create_summary(cls, payload, omit_phase=False):
        """
        Create and return a one-line summary of the build
        """
        status_colour = {
            'SUCCESS': HookService.colors['GREEN'],
            'UNSTABLE': HookService.colors['YELLOW'],
            'FAILED': HookService.colors['RED']
        }.get(
            payload['build'].get('status', 'SUCCESS'),
            HookService.colors['RED']
        )

        lines = []

        # Build number
        lines.append(u'Jenkins CI - build #{number}'.format(
            project=payload['name'],
            number=payload['build']['number'],
        ))

        # Status
        status = u''
        if 'status' in payload['build']:
            status = u'{status_colour}{message}{RESET}'.format(
                status_colour=status_colour,
                message=payload['build']['status'].capitalize(),
                **HookService.colors
            )

        # Current phase
        phase = u''
        if not omit_phase:
            phase = u'{status_colour}{message}{RESET}'.format(
                status_colour=status_colour,
                message=payload['build']['phase'].capitalize(),
                **HookService.colors
            )

        lines.append(' | '.join(filter(bool, [phase, status])))

        # URL to build
        lines.append(u'{PINK}{url}{RESET}'.format(
            url=payload['build']['full_url'],
            **HookService.colors
        ))

        line = u' '.join(lines)
        return cls._prefix_line(line, payload)

    @classmethod
    def form(cls):
        return JenkinsConfigForm
