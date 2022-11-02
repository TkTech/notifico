import re

import flask_wtf as wtf
from functools import wraps
from wtforms.fields import SelectMultipleField
from wtforms import fields, validators

from notifico.contrib.services import EnvironmentMixin
from notifico.services.hook import IncomingHookService

COMMIT_MESSAGE_LENGTH_LIMIT = 1000


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

    # Try to find the branch/tag name from `ref`, falling back to `base_ref`
    ref_r = re.compile(r'refs/(heads|tags)/(.*)$')
    if 'ref' in payload:
        match = ref_r.match(payload['ref'])
        if match:
            type_, name = match.group(1, 2)
            result[{'heads': 'branch', 'tags': 'tag'}[type_]] = name

    if 'pusher' in payload:
        result['pusher'] = payload['pusher'].get('username', 'Unknown')

    # Summarize file movement over all the commits
    for commit in payload.get('commits', tuple()):
        for type_ in ('added', 'removed', 'modified'):
            if commit[type_]:
                result['files'][type_].extend(commit[type_])
                result['files']['all'].extend(commit[type_])

    return result


def is_event_allowed(config, category, event):
    if not config or not config.get('events'):
        # not whitelisting events, show everything
        return True
    # build a name like pr_opened or issue_assigned
    event_name = '{0}_{1}'.format(category, event) if event else category

    return event_name in config['events']


def action_filter(category, action_key='action'):
    def decorator(f):
        @wraps(f)
        def wrapper(cls, user, request, hook, json):
            event = json[action_key] if action_key else None
            if is_event_allowed(hook.config, category, event):
                return f(cls, user, request, hook, json)
        return wrapper
    return decorator


class EventSelectField(SelectMultipleField):
    def __call__(self, *args, **kwargs):
        kwargs['style'] = 'height: 25em; width: auto;'
        return SelectMultipleField.__call__(self, *args, **kwargs)


class GiteaConfigForm(wtf.FlaskForm):
    branches = fields.StringField('Branches', validators=[
        validators.Optional(),
        validators.Length(max=1024)
    ], description=(
        'A comma-separated list of branches to forward, or blank for all.'
        ' Ex: "master, dev"'
    ))
    events = EventSelectField('Events', choices=[
        ('create_branch',                'Create branch'),
        ('create_tag',                   'Create tag'),
        ('delete_branch',                'Delete branch'),
        ('delete_tag',                   'Delete tag'),
        ('push',                         'Push'),
        ('repository_created',           'Repository: created'),
        ('repository_deleted',           'Repository: deleted'),
        ('fork',                         'Repository: forked'),
        ('release_published',            'Release published'),
        ('release_updated',              'Release updated'),
        ('release_deleted',              'Release deleted'),
        ('issue_opened',                 'Issue: opened'),
        ('issue_closed',                 'Issue: closed'),
        ('issue_reopened',               'Issue: reopened'),
        ('issue_edited',                 'Issue: edited'),
        ('issue_assigned',               'Issue: assigned'),
        ('issue_unassigned',             'Issue: unassigned'),
        ('issue_label_updated',          'Issue: label updated'),
        ('issue_label_cleared',          'Issue: label cleared'),
        ('issue_milestoned',             'Issue: milestoned'),
        ('issue_demilestoned',           'Issue: demilestoned'),
        ('issue_comment_created',        'Issue comment'),
        ('issue_comment_edited',         'Issue comment: edited'),
        ('issue_comment_deleted',        'Issue comment: deleted'),
        ('pull_request_opened',          'Pull request: opened'),
        ('pull_request_closed',          'Pull request: closed'),
        ('pull_request_reopened',        'Pull request: reopened'),
        ('pull_request_edited',          'Pull request: edited'),
        ('pull_request_assigned',        'Pull request: assigned'),
        ('pull_request_unassigned',      'Pull request: unassigned'),
        ('pull_request_label_updated',   'Pull request: label updated'),
        ('pull_request_label_cleared',   'Pull request: label cleared'),
        ('pull_request_milestoned',      'Pull request: milestoned'),
        ('pull_request_demilestoned',    'Pull request: demilestoned'),
        ('pull_request_synchronize',     'Pull request: synchronize'),
        ('pull_request_comment_created', 'Pull request comment: created'),
        ('pull_request_comment_edited',  'Pull request comment: edited'),
        ('pull_request_comment_deleted', 'Pull request comment: deleted'),
        ('pull_request_review_approved', 'Pull request review: approved'),
        ('pull_request_review_rejected', 'Pull request review: rejected'),
        ('pull_request_review_comment',  'Pull request review: commented')
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
    prefer_username = fields.BooleanField('Prefer Usernames', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, show Gitea usernames instead of commiter name when'
        ' possible.'
    ))
    full_project_name = fields.BooleanField('Full Project Name', validators=[
        validators.Optional()
    ], default=False, description=(
        'If checked, show the full Gitea project name (ex: notifico/notifico)'
        ' instead of the Notifico project name (ex: notifico)'
    ))
    title_only = fields.BooleanField('Title Only', validators=[
        validators.Optional()
    ], default=False, description=(
        'If checked, only the commits title (the commit message up to'
        ' the first new line) will be emitted.'
    ))


def _create_push_summary(project_name, j, config):
    """
    Create and return a one-line summary of the push in `j`.
    """
    original = j['original']
    show_branch = config.get('show_branch', True)

    # Build the push summary.
    line = []

    line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
        name=project_name,
        **IncomingHookService.colors
    ))

    # The user doing the push.
    line.append(u'{ORANGE}{pusher}{RESET} pushed'.format(
        pusher=j['pusher'],
        **IncomingHookService.colors
    ))

    # The number of commits included in this push.
    line.append(u'{GREEN}{count}{RESET} {commits}'.format(
        count=len(original['commits']),
        commits='commit' if len(original['commits']) == 1 else 'commits',
        **IncomingHookService.colors
    ))

    if show_branch and j['branch']:
        line.append(u'to {GREEN}{branch}{RESET}'.format(
            branch=j['branch'],
            **IncomingHookService.colors
        ))

    # File movement summary.
    line.append(u'[+{added}/-{removed}/\u00B1{modified}]'.format(
        added=len(j['files']['added']),
        removed=len(j['files']['removed']),
        modified=len(j['files']['modified'])
    ))

    # The shortened URL linking to the compare page.
    if original['compare_url']:
        line.append(u'{PINK}{compare_link}{RESET}'.format(
            compare_link=GiteaHook.shorten(original['compare_url']),
            **IncomingHookService.colors
        ))

    return u' '.join(line)


def _create_commit_summary(project_name, j, config):
    """
    Create and yield a one-line summary of each commit in `j`.
    """
    prefer_username = config.get('prefer_username', True)
    title_only = config.get('title_only', False)

    original = j['original']

    for commit in original['commits']:
        committer = commit.get('committer', {})
        author = commit.get('author', {})

        line = []

        line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
            name=project_name,
            **IncomingHookService.colors
        ))

        line.append(u'{GREEN}{sha}{RESET}'.format(
            sha=commit['id'][:7],
            **IncomingHookService.colors
        ))

        line.append(u'-')

        # Show the committer.
        attribute_to = None
        if prefer_username:
            attribute_to = author.get('username')
            if not attribute_to:
                attribute_to = committer.get('username')
        if not attribute_to:
            attribute_to = author.get('name')
            if not attribute_to:
                attribute_to = committer.get('name')

        if attribute_to:
            line.append(u'{ORANGE}{attribute_to}{RESET}'.format(
                attribute_to=attribute_to,
                **IncomingHookService.colors
            ))
            line.append(u'-')

        message = commit['message']
        message_lines = message.split('\n')
        if title_only and len(message_lines) > 0:
            message = message_lines[0]
        # Cap the commit message to 1000 characters, this should be around two
        # lines on IRC and stops really long messages from spamming channels.
        if len(message) > COMMIT_MESSAGE_LENGTH_LIMIT:
            message = message[:COMMIT_MESSAGE_LENGTH_LIMIT] + '...'
        line.append(message)

        yield u' '.join(line)


def _create_push_final_summary(project_name, j, config):
    # The name of the repository.
    original = j['original']
    line_limit = config.get('line_limit', 3)

    line = []

    line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
        name=project_name,
        **IncomingHookService.colors
    ))

    line.append(u'... and {count} more commits.'.format(
        count=len(original.get('commits', [])) - line_limit
    ))

    return u' '.join(line)


class GiteaHook(EnvironmentMixin, IncomingHookService):
    SERVICE_NAME = 'Gitea'
    SERVICE_ID = 100

    @classmethod
    def service_description(cls):
        return cls.env().get_template('gitea_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        payload = request.get_json()
        if not payload:
            return

        event = request.headers.get('X-Gitea-Event', '')

        event_handler = {
            'create': cls._handle_create,
            'delete': cls._handle_delete,
            'fork': cls._handle_fork,
            'push': cls._handle_push,
            'issues': cls._handle_issues,
            'issue_comment': cls._handle_issue_comment,
            'pull_request': cls._handle_pull_request,
            'pull_request_approved': cls._handle_pull_request_approved,
            'pull_request_rejected': cls._handle_pull_request_rejected,
            'release': cls._handle_release
        }

        if event not in event_handler:
            return

        return event_handler[event](user, request, hook, payload)

    @classmethod
    @action_filter('create', 'ref_type')
    def _handle_create(cls, user, request, hook, json):
        fmt_string = u' '.join([
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} '
            'created {ref_type}',
            # null/None if repository was created
            u'{GREEN}{ref}{RESET}' if json['ref'] else u'',
            u'- {PINK}{url}{RESET}'
        ])

        # URL points to repo, no other url available
        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            ref_type=json['ref_type'],
            ref=json['ref'],
            url=GiteaHook.shorten(json['repository']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    @action_filter('delete', 'ref_type')
    def _handle_delete(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} deleted '
            '{ref_type} {GREEN}{ref}{RESET} - {PINK}{url}{RESET}'
        )

        # URL points to repo, no other url available
        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            ref_type=json['ref_type'],
            ref=json['ref'],
            url=GiteaHook.shorten(json['repository']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    @action_filter('fork', None)
    def _handle_fork(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} forked '
            'the repository - {PINK}{url}{RESET}'
        )

        # URL points to repo, no other url available
        yield fmt_string.format(
            name=json['forkee']['name'],
            who=json['repository']['owner']['login'],
            url=GiteaHook.shorten(json['repository']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    @action_filter('push', None)
    def _handle_push(cls, user, request, hook, json):
        j = simplify_payload(json)
        original = j['original']

        # Config may not exist for pre-migrate hooks.
        config = hook.config or {}
        # Should we get rid of mIRC colors before sending?
        strip = not config.get('use_colors', True)
        # Branch names to filter on.
        branches = config.get('branches', None)
        # Display tag activity?
        show_tags = config.get('show_tags', True)
        # Limit the number of lines to display before the summary.
        # 3 is the default on github.com's IRC service
        line_limit = config.get('line_limit', 3)
        # The use wants the <username>/<project name> form from
        # github, not the Notifico name.
        full_project_name = config.get('full_project_name', False)

        if branches:
            # The user wants to filter by branch name.
            branches = [b.strip().lower() for b in branches.split(',')]
            if j['branch'] and j['branch'].lower() not in branches:
                # This isn't a branch the user wants.
                return

        if not original['commits']:
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
            # No commits, no tags, no new branch. Nothing to do
            return

        project_name = original['repository']['name']
        if full_project_name:
            project_name = '{username}/{project_Name}'.format(
                username=original['repository']['owner']['name'],
                project_Name=project_name
            )

        # A short summarization of the commits in the push.
        yield cls.message(
            _create_push_summary(project_name, j, config),
            strip=strip
        )

        # A one-line summary for each commit in the push.
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
    @action_filter('issue')
    def _handle_issues(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} '
            'issue {GREEN}#{num}{RESET}{ORANGE}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            action=json['action'],
            num=json['issue']['number'],
            title=json['issue']['title'],
            url=GiteaHook.shorten(json['issue']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    def _handle_issue_comment(cls, user, request, hook, json):
        event_extended_type = request.headers.get('X-Gitea-Event-Type', '')
        if event_extended_type == 'pull_request_comment' and json['action'] == 'reviewed':
            if is_event_allowed(hook.config, 'pull_request_review_comment', None):
                yield cls._create_pull_request_comment(json)
            return

        if not 'is_pull' in json:
            return

        event_type = 'issue_comment' if not json['is_pull'] else 'pull_request_comment'
        if not is_event_allowed(hook.config, event_type, json['action']):
            return

        action_dict = {
            'created': 'commented',
            'edited': 'edited a comment',
            'deleted': 'deleted a comment',
            'reviewed': 'reviewed'
        }
        action = action_dict.get(json['action'], '')
        if not action:
            return

        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} on '
            '{issue_type} {GREEN}#{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            action=action,
            issue_type='pull request' if json['is_pull'] else 'issue',
            num=json['issue']['number'],
            title=json['issue']['title'],
            url=GiteaHook.shorten(json['comment']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    @action_filter('pull_request')
    def _handle_pull_request(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} pull '
            'request {GREEN}#{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            action=json['action'],
            num=json['pull_request']['number'],
            title=json['pull_request']['title'],
            url=GiteaHook.shorten(json['pull_request']['html_url']),
            **IncomingHookService.colors
        )


    @classmethod
    @action_filter('pull_request_review_approved', None)
    def _handle_pull_request_approved(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} pull '
            'request {GREEN}#{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            action='approved',
            num=json['pull_request']['number'],
            title=json['pull_request']['title'],
            url=GiteaHook.shorten(json['pull_request']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    @action_filter('pull_request_review_rejected', None)
    def _handle_pull_request_rejected(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} pull '
            'request {GREEN}#{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            action='rejected',
            num=json['pull_request']['number'],
            title=json['pull_request']['title'],
            url=GiteaHook.shorten(json['pull_request']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    @action_filter('release')
    def _handle_release(cls, user, request, hook, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} '
            'release {GREEN}{tag_name} | {title}{RESET} - {PINK}{url}{RESET}'
        )

        yield fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            action=json['action'],
            tag_name=json['release']['tag_name'],
            title=json['release']['name'],
            url=GiteaHook.shorten(json['release']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    def _create_non_commit_summary(cls, j, config):
        """
        Create and return a one-line summary of things not involving commits
        in `j`.
        """
        original = j['original']
        full_project_name = config.get('full_project_name', False)

        line = []

        # The name of the repository.
        project_name = original['repository']['name']
        if full_project_name:
            # The use wants the <username>/<project name> form from
            # github, not the Notifico name.
            project_name = '{username}/{project_Name}'.format(
                username=original['repository']['owner']['name'],
                project_Name=project_name
            )

        line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
            name=project_name,
            **IncomingHookService.colors
        ))

        # The user doing the push, if available.
        if j['pusher']:
            line.append(u'{ORANGE}{pusher}{RESET}'.format(
                pusher=j['pusher'],
                **IncomingHookService.colors
            ))

        if j['tag']:
            if not original.get('head_commit'):
                if not is_event_allowed(config, 'delete', 'tag'):
                    return ''
                line.append(u'deleted' if j['pusher'] else u'Deleted')
                line.append(u'tag')
            else:
                if not is_event_allowed(config, 'create', 'tag'):
                    return ''
                # Verb with proper capitalization
                line.append(u'tagged' if j['pusher'] else u'Tagged')

                # The sha1 hash of the head (tagged) commit.
                line.append(u'{GREEN}{sha}{RESET} as'.format(
                    sha=original['head_commit']['id'][:7],
                    **IncomingHookService.colors
                ))

            # The tag itself.
            line.append(u'{GREEN}{tag}{RESET}'.format(
                tag=j['tag'],
                **IncomingHookService.colors
            ))
        elif j['branch']:
            # Verb with proper capitalization
            if original['deleted']:
                if not is_event_allowed(config, 'delete', 'branch'):
                    return ''
                line.append(
                    u'deleted branch' if j['pusher'] else u'Deleted branch'
                )
            else:
                if not is_event_allowed(config, 'create', 'branch'):
                    return ''
                line.append(
                    u'created branch' if j['pusher'] else u'Created branch'
                )

            # The branch name
            line.append(u'{GREEN}{branch}{RESET}'.format(
                branch=j['branch'],
                **IncomingHookService.colors
            ))

        if original['head_commit']:
            # The shortened URL linking to the head commit.
            line.append(u'{PINK}{link}{RESET}'.format(
                link=GiteaHook.shorten(original['head_commit']['url']),
                **IncomingHookService.colors
            ))

        return u' '.join(line)

    @classmethod
    def _create_pull_request_comment(cls, json):
        fmt_string = (
            u'{RESET}[{BLUE}{name}{RESET}] {ORANGE}{who}{RESET} {action} pull '
            'request {GREEN}#{num}{RESET}: {title} - {PINK}{url}{RESET}'
        )

        return fmt_string.format(
            name=json['repository']['name'],
            who=json['sender']['login'],
            action='reviewed',
            num=json['pull_request']['number'],
            title=json['pull_request']['title'],
            url=GiteaHook.shorten(json['pull_request']['html_url']),
            **IncomingHookService.colors
        )

    @classmethod
    def form(cls):
        return GiteaConfigForm
