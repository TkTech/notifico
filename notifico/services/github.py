# -*- coding: utf8 -*-
import re
import json
import requests

from flask.ext import wtf

from notifico.services.service import Service


class GithubConfigForm(wtf.Form):
    branches = wtf.TextField('Branches', validators=[
        wtf.Optional()
    ], description=(
        'A comma-seperated list of branches to forward, or blank for all.'
        ' Ex: "master, dev"'
    ))


def _irc_format(hook, j, commit):
    """
    Formats a Github commit destined for IRC.
    """
    line = []
    # Add the project name.
    line.append('{RESET}[{BLUE}{0}{RESET}]'.format(
        j['repository']['name'],
        **Service.COLORS
    ))
    line.append('{LIGHT_CYAN}{0}{RESET}'.format(
        commit['author']['username'],
        **Service.COLORS
    ))
    line.append('{PINK}{0}{RESET}'.format(
        commit['id'][:7],
        **Service.COLORS
    ))
    line.append(commit['message'][:50] + (commit['message'][75:] and '...'))
    return ' '.join(line)


def _fmt_summary(hook, j):
    line = []
    line.append('{RESET}[{BLUE}{0}{RESET}]'.format(
        j['repository']['name'],
        **Service.COLORS
    ))
    line.append('{0} pushed {RED}{1}{RESET} {3}'.format(
        j['pusher']['name'],
        len(j['commits']),
        'commit' if len(j['commits']) == 1 else 'commits',
        **Service.COLORS
    ))
    line.append('{PINK}{0}{RESET}'.format(
        GithubService.shorten(j['compare']),
        **Service.COLORS
    ))
    return ' '.join(line)


class GithubService(Service):
    """
    Service hook for http://github.com.
    """
    @staticmethod
    def service_id():
        return 10

    @staticmethod
    def service_name():
        return 'Github'

    @staticmethod
    def service_url():
        return 'http://github.com'

    @staticmethod
    def service_form():
        return GithubConfigForm

    @staticmethod
    def service_description():
        return GithubService.env().get_template('github_desc.html').render()

    @staticmethod
    def handle_request(user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            return

        j = json.loads(p)

        if 'commits' in j:
            yield dict(
                type='message',
                payload=dict(
                    msg=_fmt_summary(hook, j),
                    type=Service.COMMIT
                )
            )

            # There are some new commits in this message.
            for commit in j['commits']:
                yield dict(
                    type='message',
                    payload=dict(
                        msg=_irc_format(hook, j, commit),
                        type=Service.COMMIT
                    )
                )

    @classmethod
    def shorten(cls, url):
        # Make sure the URL hasn't already been shortened, since github
        # may does this in the future for web hooks. Better safe than silly.
        if re.search(r'^https?://git.io', url):
            return url

        return requests.post('http://git.io', data={
            'url': url
        }).headers['Location']
