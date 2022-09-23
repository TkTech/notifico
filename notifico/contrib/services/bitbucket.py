import json

import flask_wtf as wtf
from wtforms import fields, validators

from notifico.contrib.services import BundledService


class BitbucketConfigForm(wtf.FlaskForm):
    branches = fields.StringField('Branches', validators=[
        validators.Optional(),
        validators.Length(max=1024)
    ], description=(
        'A comma-seperated list of branches to forward, or blank for all.'
        ' Ex: "master, dev"'
    ))
    use_colors = fields.BooleanField('Use Colors', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, commit messages will include minor mIRC coloring.'
    ))
    show_branch = fields.BooleanField('Show Branch Names', validators=[
        validators.Optional()
    ], default=True, description=(
        'If checked, show the branch for a commit.'
    ))
    show_raw_author = fields.BooleanField('Show Raw Author', validators=[
        validators.Optional()
    ], default=False, description=(
        'If checked, shows the raw author for a commit. For example,'
        ' <code>Tyler Kennedy &lt;tk@tkte.ch&gt;</code> instead of'
        ' <code>TkTech</code>.'
    ))


def simplify_payload(payload):
    result = {
        'branch': None,
        'tag': None,
        'pusher': None,
        'files': {
            'all': set(),
            'added': set(),
            'removed': set(),
            'modified': set()
        },
        'original': payload
    }

    for commit in payload.get('commits', tuple()):
        # Summarize file changes among all the commits
        # in this push.
        for file_ in commit.get('files', tuple()):
            type_, name = file_['type'], file_['file']
            result['files'][type_].add(name)
            result['files']['all'].add(name)

        # Usually only the last commit in the chain will
        # include the "branch" or "branches" tag.
        branch = commit.get('branch')
        if branch:
            result['branch'] = branch

    # The username of whoever made this push.
    result['pusher'] = payload.get('user')

    return result


def _make_summary_line(hook, j, config):
    """
    Create a formatted line summarizing the commits in `j`.
    """
    original = j['original']
    show_branch = config.get('show_branch', True)

    # Buffer for the line summary.
    line = []

    # Project name
    line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
        name=original['repository']['name'],
        **BundledService.colors
    ))

    if j['pusher']:
        line.append(u'{ORANGE}{pusher}{RESET} pushed'.format(
            pusher=j['pusher'],
            **BundledService.colors
        ))

    # Commit count
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

    # TODO: We can apparently build URLs to show comparisons
    #       using /compare/<lc>..<lr>, which is completely
    #       undocumented. For now build a link to the last
    #       commit in the set.
    link = u'{0}{1}commits/'.format(
        original['canon_url'],
        original['repository']['absolute_url'],
        original['commits'][-1]['node']
    )
    line.append(u'{PINK}{0}{RESET}'.format(
        BitbucketHook.shorten(link),
        **BundledService.colors
    ))

    return u' '.join(line)


def _make_commit_line(hook, j, commit):
    """
    Create a formatted line summarizing the single commit `commit`.
    """
    line = []

    original = j['original']
    config = hook.config or {}
    show_raw_author = config.get('show_raw_author', False)

    line.append(u'{RESET}[{BLUE}{name}{RESET}]'.format(
        name=original['repository']['name'],
        **BundledService.colors
    ))

    line.append(u'{ORANGE}{0}{RESET}'.format(
        commit['raw_author'] if show_raw_author else commit['author'],
        **BundledService.colors
    ))

    line.append(u'{GREEN}{0}{RESET}'.format(
        commit['node'][:7],
        **BundledService.colors
    ))

    line.append(u'-')
    line.append(commit['message'])

    return u' '.join(line)


class BitbucketHook(BundledService):
    SERVICE_NAME = 'Bitbucket'
    SERVICE_ID = 30

    @classmethod
    def service_description(cls):
        return cls.env().get_template('bitbucket_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            return

        j = simplify_payload(json.loads(p))
        original = j['original']

        config = hook.config or {}
        strip = not config.get('use_colors', True)
        branches = config.get('branches', None)

        if not original['commits']:
            # TODO: No commits, nothing to do. We should add an option for
            # showing tag activity.
            return

        if branches:
            branches = [b.strip().lower() for b in branches.split(',')]
            if j['branch'] and j['branch'].lower() not in branches:
                # This isn't a branch the user wants.
                return

        yield cls.message(_make_summary_line(hook, j, config), strip=strip)
        for commit in original['commits']:
            yield cls.message(_make_commit_line(hook, j, commit), strip=strip)

    @classmethod
    def form(cls):
        return BitbucketConfigForm
