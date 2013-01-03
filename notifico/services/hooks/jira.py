# -*- coding: utf8 -*-
__all__ = ('JIRAHook',)
from urlparse import urlsplit

from flask.ext import wtf

from notifico.services.hooks import HookService


def _simplify(j):
    simplified = {
        'who_username': None,
        'who_name': None,
        'project_key': None,
        'issue_key': None,
        'issue_title': None,
        'host': None,
        'link': None,
        'changes': {},
        'comment': None
    }

    # Extract user information.
    user = j['user']
    simplified['who_username'] = user.get('name')
    simplified['who_name'] = user.get('displayName')

    # Extract issue information.
    issue = j['issue']
    simplified['issue_key'] = issue.get('key')
    simplified['host'] = urlsplit(issue['self']).hostname
    simplified['link'] = 'http://{host}/browse/{key}'.format(
        host=simplified['host'],
        key=simplified['issue_key']
    )
    simplified['issue_title'] = issue.get('fields', {}).get('summary')

    simplified['comment'] = j.get('comment', {}).get('body')

    project = issue.get('fields', {}).get('project', {})
    simplified['project_key'] = project.get('key')

    # Find any field changes made in this update.
    items = j.get('changelog', {}).get('items', [])
    for item in items:
        simplified['changes'][item['field']] = item['toString']

    return simplified


class JIRAConfigForm(wtf.Form):
    use_colors = wtf.BooleanField('Use Colors', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, messages will include minor mIRC coloring.'
    ))
    prefer_username = wtf.BooleanField('Prefer Usernames', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, prefer displaying JIRA account names instead of'
        ' full names.'
    ))


class JIRAHook(HookService):
    """
    HookService hook for Atlassian's JIRA service.
    """
    SERVICE_NAME = 'JIRA'
    SERVICE_ID = 40

    @classmethod
    def service_description(cls):
        return cls.env().get_template('jira_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        j = request.json
        config = hook.config or {}
        # Should we get rid of mIRC colors before sending?
        strip = not config.get('use_colors', True)

        # Identify the type of incoming event.
        event = j.get('webhookEvent')
        handler = {
            'jira:issue_updated': cls._jira_event_issue_updated,
            'jira:issue_created': cls._jira_event_issue_created
        }.get(event, cls._jira_event_unknown)

        for message in handler(j, config):
            yield cls.message(message, strip=strip)

    @classmethod
    def _jira_event_unknown(self, j, config):
        return []

    @classmethod
    def _jira_event_issue_created(self, j, config):
        prefer_username = config.get('prefer_username', True)
        line = []
        simplified = _simplify(j)

        # Build our message output.
        # What project was the change made on?
        if simplified['project_key']:
            line.append('{RESET}[{BLUE}{name}{RESET}]'.format(
                name=simplified['project_key'],
                **HookService.colors
            ))
        # Who made the change?
        attribute_to = None
        if prefer_username:
            attribute_to = simplified['who_username']
        if attribute_to is None:
            attribute_to = simplified['who_name']

        if attribute_to:
            line.append('{LIGHT_CYAN}{attribute_to}{RESET} created'.format(
                attribute_to=attribute_to,
                **HookService.colors
            ))

        # What was changed?
        if simplified['issue_key']:
            line.append('{PINK}{key}{RESET}'.format(
                key=simplified['issue_key'],
                **HookService.colors
            ))
        if simplified['issue_title']:
            line.append(simplified['issue_title'])

        yield ' '.join(line)

        # Build the next line with link details.
        if simplified['link']:
            line = []
            if simplified['project_key']:
                line.append('{RESET}[{BLUE}{name}{RESET}]'.format(
                    name=simplified['project_key'],
                    **HookService.colors
                ))
            line.append(simplified['link'])
            yield ' '.join(line)

    @classmethod
    def _jira_event_issue_updated(self, j, config):
        prefer_username = config.get('prefer_username', True)
        line = []

        simplified = _simplify(j)

        # Build our message output.
        # What project was the change made on?
        if simplified['project_key']:
            line.append('{RESET}[{BLUE}{name}{RESET}]'.format(
                name=simplified['project_key'],
                **HookService.colors
            ))
        # Who made the change?
        attribute_to = None
        if prefer_username:
            attribute_to = simplified['who_username']
        if attribute_to is None:
            attribute_to = simplified['who_name']

        if attribute_to:
            line.append('{LIGHT_CYAN}{attribute_to}{RESET} updated'.format(
                attribute_to=attribute_to,
                **HookService.colors
            ))

        # What was changed?
        if simplified['issue_key']:
            line.append('{PINK}{key}{RESET}'.format(
                key=simplified['issue_key'],
                **HookService.colors
            ))
        if simplified['changes']:
            changes = simplified['changes']
            line.append(' -'.join([
                '{0} set to "{1}"'.format(k, v) for k, v in changes.items()
            ]))

        yield ' '.join(line)

        # Build the next line with the comment blurb.
        if simplified['comment']:
            line = []
            if simplified['project_key']:
                line.append('{RESET}[{BLUE}{name}{RESET}]'.format(
                    name=simplified['project_key'],
                    **HookService.colors
                ))
            line.append(simplified['comment'])
            yield ' '.join(line)

        # Build the next line with link details.
        if simplified['link']:
            line = []
            if simplified['project_key']:
                line.append('{RESET}[{BLUE}{name}{RESET}]'.format(
                    name=simplified['project_key'],
                    **HookService.colors
                ))
            line.append(simplified['link'])
            yield ' '.join(line)

    @classmethod
    def form(cls):
        return JIRAConfigForm
