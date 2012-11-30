# -*- coding: utf8 -*-
__all__ = ('GithubHook',)

import re
import json
import requests

from flask.ext import wtf

from notifico.services.hooks import HookService


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
        **HookService.colors
    ))
    line.append('{LIGHT_CYAN}{0}{RESET}'.format(
        commit['author']['username'],
        **HookService.colors
    ))
    line.append('{PINK}{0}{RESET}'.format(
        commit['id'][:7],
        **HookService.colors
    ))
    line.append(commit['message'].split('\n', 1)[0])
    return ' '.join(line)


def _fmt_summary(hook, j):
    line = []
    line.append('{RESET}[{BLUE}{0}{RESET}]'.format(
        j['repository']['name'],
        **HookService.colors
    ))
    line.append('{0} pushed {RED}{1}{RESET} {2}'.format(
        j['pusher']['name'],
        len(j['commits']),
        'commit' if len(j['commits']) == 1 else 'commits',
        **HookService.colors
    ))
    line.append('{PINK}{0}{RESET}'.format(
        GithubHook.shorten(j['compare']),
        **HookService.colors
    ))
    return ' '.join(line)


class GithubHook(HookService):
    """
    HookService hook for http://github.com.
    """
    SERVICE_NAME = 'Github'
    SERVICE_ID = 10

    @classmethod
    def service_description(cls):
        return cls.env().get_template('github_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            return

        j = json.loads(p)
        # Config may not exist for pre-migrate hooks.
        config = hook.config or {}
        # Should we get rid of mIRC colors before sending?
        strip = not config.get('use_colors', True)

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

        # Only github URLs can be shortened by the git.io service, which
        # will return a 201 created on success and return the new url
        # in the Location header.
        try:
            r = requests.post('http://git.io', data={
                'url': url
            }, timeout=4.0)
        except requests.exceptions.Timeout:
            return url

        # Something went wrong, usually means we're being throttled.
        # TODO: If we are being throttled, handle this smarter instead
        #       of trying again on the next message.
        if r.status_code != 201:
            return url

        return r.headers['Location']

    @classmethod
    def form(cls):
        return GithubConfigForm
