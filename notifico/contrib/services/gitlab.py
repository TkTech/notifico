import re

import flask_wtf as wtf
from wtforms import fields, validators
from functools import wraps
from wtforms.fields import SelectMultipleField

from notifico.contrib.services import BundledService


def simplify_payload(payload):
    result = {
        'branch': None,
        'tag': None,
        'pusher': None,
        'files': {
            'all': [],
            'added': [],
            'removed': [],
            'modified': []
        },
        'original': payload
    }

    # Try to find the branch/tag name from `ref`.
    match = re.match(r'refs/(heads|tags)/(.*)$', payload.get('ref', ''))
    if match:
        type_, name = match.group(1, 2)
        result[{'heads': 'branch', 'tags': 'tag'}[type_]] = name

    # The name of whoever made this push
    result['pusher'] = payload.get('user_name')

    # Summarize file movement over all the commits.
    for commit in payload.get('commits', []):
        for type_ in ('added', 'removed', 'modified'):
            result['files'][type_].extend(commit[type_])
            result['files']['all'].extend(commit[type_])

    return result


def is_event_allowed(config, category, event):
    if not config or not config.get('events'):
        # not whitelisting events, show everything
        return True

    # build a name like mr_opened or issue_assigned
    event_name = '{0}_{1}'.format(category, event) if event else category

    return event_name in config['events']


def action_filter(category, action_key='action'):
    def decorator(f):
        @wraps(f)
        def wrapper(cls, user, request, hook, json):
            event = json['object_attributes'][action_key] if action_key else None
            if is_event_allowed(hook.config, category, event):
                return f(cls, user, request, hook, json)

        return wrapper
    return decorator


class EventSelectField(SelectMultipleField):
    def __call__(self, *args, **kwargs):
        kwargs['style'] = 'height: 25em; width: auto;'
        return SelectMultipleField.__call__(self, *args, **kwargs)


class GitlabConfigForm(wtf.FlaskForm):
    branches = fields.StringField('Branches', validators=[
        validators.Optional(),
        validators.Length(max=1024)
    ], description=(
        'A comma-separated of branches to forward, or blank for all.'
        ' Ex: "master, dev"'
    ))
    events = EventSelectField('Events', choices=[
        ('commit_comment',             'Commit comment'),
        ('snippet_comment',            'Snippet comment'),
        ('pipeline_created',           'Pipeline status: created'),
        ('pipeline_pending',           'Pipeline status: pending'),
        ('pipeline_running',           'Pipeline status: running'),
        ('pipeline_failed',            'Pipeline status: failed'),
        ('pipeline_success',           'Pipeline status: success'),
        ('pipeline_canceled',          'Pipeline status: canceled'),
        ('pipeline_skipped',           'Pipeline status: skipped'),
        ('build_created',              'Build status: created'),
        ('build_pending',              'Build status: pending'),
        ('build_running',              'Build status: running'),
        ('build_failed',               'Build status: failed'),
        ('build_success',              'Build status: success'),
        ('build_canceled',             'Build status: canceled'),
        ('build_skipped',              'Build status: skipped'),
        ('create_branch',              'Create branch'),
        ('create_tag',                 'Create tag'),
        ('delete_branch',              'Delete branch'),
        ('delete_tag',                 'Delete tag'),
        ('issue_comment',              'Issue comment'),
        ('issue_close',                'Issue: closed'),
        ('issue_update',               'Issue: updated'),
        ('issue_open',                 'Issue: opened'),
        ('issue_reopen',               'Issue: reopened'),
        ('mr_comment',                 'Merge request comment'),
        ('mr_close',                   'Merge request: closed'),
        ('mr_update',                  'Merge request: updated'),
        ('mr_open',                    'Merge request: opened'),
        ('mr_reopen',                  'Merge request: reopened'),
        ('mr_merge',                   'Merge request: merged'),
        ('push',                       'Push'),
        ('wiki_create',                'Wiki: created page'),
        ('wiki_edit',                  'Wiki: edited page')
    ])
    use_colors = fields.BooleanField('Use Colors', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, commit messages will include minor mIRC coloring.'
    ))
    show_branch = fields.BooleanField('Show Branch Name', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, commit messages will include the branch name.'
    ))
    show_tags = fields.BooleanField('Show Tags', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, changes to tags will be shown.'
    ))
    full_project_name = fields.BooleanField('Full Project Name', validators=[
        validators.Optional()
    ], default=False, description=(
        'If checked, show the full gitlab project name (ex: tktech/notifico)'
        ' instead of the Notifico project name (ex: notifico)'
    ))
    title_only = fields.BooleanField('Title Only', validators=[
        validators.Optional()
    ], default=False, description=(
        'If checked, only the commits title (the commit message up to'
        ' the first new line) will be emitted.'
    ))


def _create_push_summary(project_name, j, config):
    original = j['original']
    show_branch = config.get('show_branch', True)

    # Build the push summary.
    line = []

    line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
        name=project_name,
        **BundledService.colors
    ))

    # The user doing the push.
    line.append(u'{ORANGE}{pusher}{RESET} pushed'.format(
        pusher=j['pusher'],
        **BundledService.colors
    ))

    # The number of commits included in this push.
    line.append(u'{GREEN}{count}{RESET} {commits}'.format(
        count=len(original['commits']),
        commits='commit' if len(original['commits']) == 1 else 'commits',
        **BundledService.colors
    ))

    if show_branch and j['branch']:
        line.append(u'to {GREEN}{branch}{RESET}'.format(
            branch=j['branch'],
            **BundledService.colors
        ))

    # File movement summary.
    line.append(u'[+{added}/-{removed}/\u00B1{modified}]'.format(
        added=len(j['files']['added']),
        removed=len(j['files']['removed']),
        modified=len(j['files']['modified'])
    ))

    # Build a compare url.
    # If this is the first push, link to the after commit.
    if re.match(r'0+', original['before']):
        link = '{0}/commit/{1}'.format(
            original['project']['web_url'],
            original['after']
        )
    else:
        link = '{0}/compare/{1}...{2}'.format(
            original['project']['web_url'],
            original['before'],
            original['after']
        )
    line.append(u'{PINK}{0}{RESET}'.format(
        GitlabHook.shorten(link),
        **BundledService.colors
    ))

    return u' '.join(line)


def _create_commit_summary(project_name, j, config):
    title_only = config.get('title_only', False)

    original = j['original']

    for commit in original['commits']:
        author = commit.get('author', {}).get('name')

        line = []

        line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
            name=project_name,
            **BundledService.colors
        ))

        if author:
            line.append(u'{ORANGE}{author}{RESET}'.format(
                author=author,
                **BundledService.colors
            ))

        line.append(u'{GREEN}{sha}{RESET}'.format(
            sha=commit['id'][:7],
            **BundledService.colors
        ))

        line.append(u'-')

        message = commit['message']
        if title_only:
            message_lines = message.split('\n')
            line.append(message_lines[0] if message_lines else message)
        else:
            line.append(message)

        yield u' '.join(line)


def _create_push_final_summary(project_name, j, config):
    original = j['original']
    line_limit = config.get('line_limit', 3)

    line = []

    line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
        name=project_name,
        **BundledService.colors
    ))

    line.append(u'... and {count} more commits.'.format(
        count = len(original.get('commits', [])) - line_limit
    ))

    return u' '.join(line)


class GitlabHook(BundledService):
    SERVICE_NAME = 'Gitlab'
    SERVICE_ID = 90

    @classmethod
    def service_description(cls):
        return cls.env().get_template('gitlab_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        payload = request.get_json()
        if not payload:
            return

        event = payload.get('object_kind', '')
        event_handler = {
            'push': cls._handle_push,
            'tag_push': cls._handle_push,
            'issue': cls._handle_issue,
            'note': cls._handle_note,
            'merge_request': cls._handle_merge_request,
            'wiki_page': cls._handle_wiki_page,
            'pipeline': cls._handle_pipeline,
            'build': cls._handle_build
        }

        if event not in event_handler:
            return

        return event_handler[event](user, request, hook, payload)

    @classmethod
    @action_filter('issue')
    def _handle_issue(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} '
            'issue {GREEN}#{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        action = json['object_attributes']['action']
        # Add '(e)d' so the action makes sense.
        action += 'd' if action.endswith('e') else 'ed'

        yield fmt_string.format(
            name=json['project']['name'],
            who=json['user']['username'],
            action=action,
            num=json['object_attributes']['iid'],
            title=json['object_attributes']['title'],
            url=GitlabHook.shorten(json['object_attributes']['url']),
            **BundledService.colors
        )

    @classmethod
    def _handle_note(cls, user, request, hook, json):
        note_type = json['object_attributes']['noteable_type']

        note_handler = {
            'Commit': cls._handle_commit_comment,
            'Issue': cls._handle_issue_comment,
            'MergeRequest': cls._handle_merge_request_comment,
            'Snippet': cls._handle_snippet_comment
        }

        if note_type not in note_handler:
            return

        return note_handler[note_type](user, request, hook, json)

    @classmethod
    @action_filter('issue_comment', None)
    def _handle_issue_comment(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} commented on '
            'issue {GREEN}#{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['project']['name'],
            who=json['user']['username'],
            num=json['issue']['iid'],
            title=json['issue']['title'],
            url=GitlabHook.shorten(json['object_attributes']['url']),
            **BundledService.colors
        )

    @classmethod
    @action_filter('commit_comment', None)
    def _handle_commit_comment(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} commented on '
            'commit {GREEN}{commit}{RESET} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['project']['name'],
            who=json['user']['username'],
            commit=json['commit']['id'],
            url=GitlabHook.shorten(json['object_attributes']['url']),
            **BundledService.colors
        )

    @classmethod
    @action_filter('snippet_comment', None)
    def _handle_snippet_comment(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} commented on '
            'snippet {GREEN}${num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['project']['name'],
            who=json['user']['username'],
            num=json['snippet']['id'],
            title=json['snippet']['title'],
            url=GitlabHook.shorten(json['object_attributes']['url']),
            **BundledService.colors
        )

    @classmethod
    @action_filter('mr_comment', None)
    def _handle_merge_request_comment(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} commented on '
            'merge request {GREEN}!{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['project']['name'],
            who=json['user']['username'],
            num=json['merge_request']['iid'],
            title=json['merge_request']['title'],
            url=GitlabHook.shorten(json['object_attributes']['url']),
            **BundledService.colors
        )

    @classmethod
    @action_filter('mr')
    def _handle_merge_request(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} '
            'merge request {GREEN}!{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        action = json['object_attributes']['action']
        action += 'd' if action.endswith('e') else 'ed'

        yield fmt_string.format(
            name=json['project']['name'],
            who=json['user']['username'],
            action=action,
            num=json['object_attributes']['iid'],
            title=json['object_attributes']['title'],
            url=GitlabHook.shorten(json['object_attributes']['url']),
            **BundledService.colors
        )

    @classmethod
    @action_filter('wiki')
    def _handle_wiki_page(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} '
            'page {GREEN}{pname}{RESET} - {PINK}{url}{RESET}'
        )

        action = json['object_attributes']['action']
        action += 'd' if action.endswith('e') else 'ed'

        yield fmt_string.format(
            name=json['project']['name'],
            who=json['user']['username'],
            action=action,
            pname=json['object_attributes']['title'],
            url=GitlabHook.shorten(json['object_attributes']['url']),
            **BundledService.colors
        )

    @classmethod
    @action_filter('pipeline', 'status')
    def _handle_pipeline(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] Pipeline {GREEN}#{num}{RESET}: '
            '{status_color}{status}{RESET} - {PINK}{url}{RESET}'
        )

        status_color = BundledService.colors['GREEN']
        if json['object_attributes']['status'].lower() != 'success':
            status_color = BundledService.colors['RED']
        link = u'{0}/pipelines/{1}'.format(
            json['project']['web_url'],
            json['object_attributes']['id']
        )

        yield fmt_string.format(
            name=json['project']['name'],
            num=json['object_attributes']['id'],
            status_color=status_color,
            status=json['object_attributes']['status'],
            url=GitlabHook.shorten(link),
            **BundledService.colors
        )

    @classmethod
    def _handle_build(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] Build {GREEN}#{num}{RESET}: '
            '{status_color}{status}{RESET} - {PINK}{url}{RESET}'
        )

        if not is_event_allowed(hook.config, 'build', json['build_status']):
            return

        status_color = BundledService.colors['GREEN']
        if json['build_status'].lower() != 'success':
            status_color = BundledService.colors['RED']
        link = 'u{0}/builds/{1}'.format(
            json['repository']['homepage'],
            json['build_id']
        )

        yield fmt_string.format(
            name=json['repository']['name'],
            num=json['build_id'],
            status_color=status_color,
            status=json['build_status'],
            url=GitlabHook.shorten(link),
            **BundledService.colors
        )

    @classmethod
    def _handle_push(cls, user, request, hook, json):
        j = simplify_payload(json)
        original = j['original']

        config = hook.config or {}
        strip = not config.get('use_colors', True)
        branches = config.get('branches', None)
        show_tags = config.get('show_tags', True)
        line_limit = config.get('line_limit', 3)
        full_project_name = config.get('full_project_name', False)

        if branches:
            branches = [b.strip().lower() for b in branches.split(',')]
            if j['branch'] and j['branch'].lower() not in branches:
                return

        if not original['commits'] or re.match(r'0+', original['before']):
            if show_tags and j['tag']:
                yield cls.message(
                    cls._create_non_commit_summary(j, config),
                    strip=strip
                )
            if j['branch']:
                yield cls.message(
                    cls._create_non_commit_summary(j, config),
                    strip=strip
                )

            return

        project_name = original['project']['name']
        if full_project_name:
            project_name = original['project']['path_with_namespace']

        if not is_event_allowed(config, 'push', None):
            return

        yield cls.message(
            _create_push_summary(project_name, j, config),
            strip=strip
        )

        line_iterator = _create_commit_summary(project_name, j, config)

        num_commits = len(j['original'].get('commits', []))
        for i, formatted_commit in enumerate(line_iterator):
            if i > line_limit or (i == line_limit and not num_commits == i+1):
                yield cls.message(_create_push_final_summary(
                    project_name,
                    j,
                    config
                ), strip=strip)
                break

            yield cls.message(formatted_commit, strip=strip)

    @classmethod
    def _create_non_commit_summary(cls, j, config):
        original = j['original']
        full_project_name = config.get('full_project_name', False)

        line = []

        project_name = original['project']['name']
        if full_project_name:
            project_name = original['project']['path_with_namespace']

        line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
            name=project_name,
            **BundledService.colors
        ))

        line.append(u'{ORANGE}{pusher}{RESET}'.format(
            pusher=j['pusher'],
            **BundledService.colors
        ))

        if j['tag']:
            if re.match(r'0+', original['after']):
                if not is_event_allowed(config, 'delete', 'tag'):
                    return ''
                line.append(u'deleted tag')
            else:
                if not is_event_allowed(config, 'create', 'tag'):
                    return ''
                line.append(u'tagged {GREEN}{sha}{RESET} as'.format(
                    sha=original['after'],
                    **BundledService.colors
                ))

            line.append(u'{GREEN}{tag}{RESET}'.format(
                tag=j['tag'],
                **BundledService.colors
            ))
        elif j['branch']:
            if re.match(r'0+', original['after']):
                if not is_event_allowed(config, 'delete', 'branch'):
                    return ''
                line.append(u'deleted branch')
            else:
                if not is_event_allowed(config, 'create', 'branch'):
                    return ''
                line.append(u'created branch')

            line.append(u'{GREEN}{branch}{RESET}'.format(
                branch=j['branch'],
                **BundledService.colors
            ))

        return u' '.join(line)

    @classmethod
    def form(cls):
        return GitlabConfigForm
