# -*- coding: utf8 -*-
__all__ = ('BitbucketHook',)

import json

from flask.ext import wtf

from notifico.services.hooks import HookService


class BitbucketConfigForm(wtf.Form):
    branches = wtf.TextField('Branches', validators=[
        wtf.Optional(),
        wtf.Length(max=1024)
    ], description=(
        'A comma-seperated list of branches to forward, or blank for all.'
        ' Ex: "master, dev"'
    ))
    use_colors = wtf.BooleanField('Use Colors', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, commit messages will include minor mIRC coloring.'
    ))
    show_branch = wtf.BooleanField('Show Branch Names', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, show the branch for a commit.'
    ))
    show_raw_author = wtf.BooleanField('Show Raw Author', validators=[
        wtf.Optional()
    ], default=False, description=(
        'If checked, shows the raw author for a commit. For example,'
        ' <code>Tyler Kennedy &lt;tk@tkte.ch&gt;</code> instead of'
        ' <code>TkTech</code>.'
    ))


def _make_summary_line(hook, j):
    """
    Create a formatted line summarizing the commits in `j`.
    """
    l = []

    # Project name
    l.append('{RESET}[{BLUE}{0}{RESET}]'.format(
        j['repository']['name'],
        **HookService.colors
    ))

    if 'name' in j:
        # For some reason we don't always get the name of the
        # pusher (not set in config?)
        l.append('{0} pushed'.format(j['name']))

    # Commit count
    l.append('{RED}{0}{RESET} {1}'.format(
        len(j['commits']),
        'commit' if len(j['commits']) == 1 else 'commits',
        **HookService.colors
    ))

    # TODO: We can apparently build URLs to show comparisons
    #       using /compare/<lc>..<lr>, which is completely
    #       undocumented. For now build a link to the last
    #       commit in the set.
    link = '{0}{1}commits/'.format(
        j['canon_url'],
        j['repository']['absolute_url'],
        j['commits'][-1]['node']
    )
    l.append('{PINK}{0}{RESET}'.format(
        BitbucketHook.shorten(link),
        **HookService.colors
    ))

    return ' '.join(l)


def _make_commit_line(hook, j, commit):
    """
    Create a formatted line summarizing the single commit `commit`.
    """
    l = []

    config = hook.config or {}
    show_branch = config.get('show_branch', True)
    show_raw_author = config.get('show_raw_author', False)

    l.append('{RESET}[{BLUE}{0}{RESET}]'.format(
        j['repository']['name'],
        **HookService.colors
    ))
    if show_branch and commit['branch']:
        l.append(commit['branch'])

    l.append('{LIGHT_CYAN}{0}{RESET}'.format(
        commit['raw_author'] if show_raw_author else commit['author'],
        **HookService.colors
    ))
    l.append('{PINK}{0}{RESET}'.format(
        commit['node'],
        **HookService.colors
    ))
    l.append(commit['message'])

    return ' '.join(l)


class BitbucketHook(HookService):
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

        j = json.loads(p)
        config = hook.config or {}
        strip = not config.get('use_colors', True)
        branches = config.get('branches', None)

        if branches:
            branches = [b.strip().lower() for b in branches.split(',')]

        # We don't always get commits in the POST payload when someone
        # is doing something funky with their repo.
        if 'commits' not in j:
            return

        if branches:
            def keep_commit(commit):
                branch = commit['branch']
                # FIXME: For whatever reason, Bitbucket thinks it's okay
                #        to send None/null as the branch name. Not sure how
                #        to handle this case.
                if branch and branch.lower() in branches:
                    return True
                return False

            # We only want to forward certain branches. Although in practice
            # a push only comes for a single branch at a time, we check
            # all of them as Bitbucket provides the field to be future-safe.
            j['commits'][:] = [c for c in j['commits'] if keep_commit(c)]
            if not j['commits']:
                # After filtering, there weren't any commits left to bother
                # with!
                return

        yield cls.message(_make_summary_line(hook, j), strip=strip)
        for commit in j['commits']:
            yield cls.message(_make_commit_line(hook, j, commit), strip=strip)

    @classmethod
    def form(cls):
        return BitbucketConfigForm
