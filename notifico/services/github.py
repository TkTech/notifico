# -*- coding: utf8 -*-
import json

from notifico.services.service import Service


def irc_format(hook, commit):
    line = []
    # Add the project name.
    line.append('{BLUE}{0}{RESET}:'.format(
        hook.project.full_name,
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
    line.append(commit['message'][:50] + (commit['message'][50:] and '...'))
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
    def handle_request(user, request, hook):
        p = request.form.get('payload', None)
        if not p:
            return

        j = json.loads(p)

        if 'commits' in j:
            # There are some new commits in this message.
            for commit in j['commits']:
                yield dict(
                    type='message',
                    payload=dict(
                        msg=irc_format(hook, commit),
                        type=Service.COMMIT
                    )
                )
            yield dict(
                type='message',
                payload=dict(
                    msg=j['compare'],
                    type=Service.COMMIT
                )
            )
