# -*- coding: utf8 -*-
import re
import json
import requests

from flask.ext import wtf

from notifico.services.service import Service


class GithubConfigForm(wtf.Form):
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


def _irc_format(hook, j, commit):
    """
    Formats a Github commit destined for IRC.
    """
    line = []
    # Add the project name.
    line.append('{RESET}[{BLUE}{0}{RESET}]'.format(
        j['repository']['name'],
        **Service.colors
    ))
    line.append('{LIGHT_CYAN}{0}{RESET}'.format(
        commit['author']['username'],
        **Service.colors
    ))
    line.append('{PINK}{0}{RESET}'.format(
        commit['id'][:7],
        **Service.colors
    ))
    line.append(commit['message'][:75] + (commit['message'][75:] and '...'))
    return ' '.join(line)


def _fmt_summary(hook, j):
    line = []
    line.append('{RESET}[{BLUE}{0}{RESET}]'.format(
        j['repository']['name'],
        **Service.colors
    ))
    line.append('{0} pushed {RED}{1}{RESET} {2}'.format(
        j['pusher']['name'],
        len(j['commits']),
        'commit' if len(j['commits']) == 1 else 'commits',
        **Service.colors
    ))
    line.append('{PINK}{0}{RESET}'.format(
        GithubService.shorten(j['compare']),
        **Service.colors
    ))
    return ' '.join(line)


class GithubService(Service):
    """
    Service hook for http://github.com.
    """
    SERVICE_NAME = 'Github'
    SERVICE_ID = 10

    @staticmethod
    def service_description():
        return GithubService.env().get_template('github_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            return

        j = json.loads(p)
        # Config may not exist for pre-migrate hooks.
        config = hook.config or {}
        # Should we get rid of mIRC colors before sending?
        strip = config.get('strip', False)

        if 'commits' in j:
            # There are some new commits in this message,
            # so send an overall summary and a per-commit
            # summary.
            yield cls.message(_fmt_summary(hook, j), strip=strip)
            for commit in j['commits']:
                yield cls.message(_irc_format(hook, j, commit), strip=strip)

    @classmethod
    def shorten(cls, url):
        # Make sure the URL hasn't already been shortened, since github
        # may does this in the future for web hooks. Better safe than silly.
        if re.search(r'^https?://git.io', url):
            return url

        return requests.post('http://git.io', data={
            'url': url
        }).headers['Location']

    @classmethod
    def form(cls):
        return GithubConfigForm

    @classmethod
    def validate(cls, form, request):
        return form.validate_on_submit()

    @classmethod
    def form_to_config(cls, form):
        return dict(
            strip=not form.use_colors.data,
            branches=form.branches.data
        )
