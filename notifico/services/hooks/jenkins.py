# -*- coding: utf8 -*-
__all__ = ('JenkinsHook',)

import json

from flask.ext import wtf

from notifico.services.hooks import HookService

def fmt_string_validator(form, field):
    fmt = field.data

    try:
        fmt.format(
            status_colour='',
            number='',
            phase='',
            status='',
            url='',
            **HookService.colors
        )
    except KeyError, e:
       raise wtf.ValidationError(
           'Invalid colour or keyword "{}"'.format(e.message)
        )
    except Exception, e:
        raise wtf.ValidationError(e.message)


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

    fmt_string = wtf.TextField('Format String', validators=[
        fmt_string_validator,
        wtf.Length(max=1024)
    ], description=(
        'A python format-string used to format the final output.<br> E.g. '

        '<code>{ORANGE}jenkins{RESET} built {status_colour}#{number}{RESET} '
        '{phase} ({status_colour}{status}{RESET}) {PINK}{url}{RESET}</code>'
    ), default=(
        '{ORANGE}jenkins{RESET} built {status_colour}#{number}{RESET} {phase} '
        '({status_colour}{status}{RESET}) {PINK}{url}{RESET}'
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

        strip = not hook.config.get('use_colors', True)
        fmt_string = hook.config.get('fmt_string',
            '{ORANGE}jenkins{RESET} built {status_colour}#{number}{RESET} '
            '{phase} ({status_colour}{status}{RESET}) {PINK}{url}{RESET}'
        )
        summary = cls._create_summary(payload, fmt_string)

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
    def _create_summary(cls, payload, fmt_string):
        """
        Create and return a one-line summary of the build
        """
        status_colour = {
            'SUCCESS': HookService.colors['GREEN'],
            'UNSTABLE': HookService.colors['ORANGE'],
            'FAILURE' : HookService.colors['RED'], # what it really is
            'FAILED': HookService.colors['RED'] # according to the docs
        }.get(
            payload['build'].get('status', 'SUCCESS'),
            HookService.colors['RED']
        )

        number = payload['build']['number']
        phase = payload['build']['phase'].lower()
        status = payload['build']['status'].lower()
        url = payload['build']['full_url']

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
