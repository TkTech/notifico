# -*- coding: utf8 -*-
__all__ = ('CIAHook',)
import xmltodict

from flask import url_for, request, abort
from flask.ext import wtf
from flask.ext.xmlrpc import XMLRPCHandler

from notifico import app, db
from notifico.services.hooks import HookService


handler = XMLRPCHandler('hub')
handler.connect(app, '/RPC2')
hub = handler.namespace('hub')


class CIAConfigForm(wtf.Form):
    use_colors = wtf.BooleanField('Use Colors', validators=[
        wtf.Optional()
    ], default=True, description=(
        'If checked, messages will include minor mIRC coloring.'
    ))


class CIAHook(HookService):
    """
    HookService hook for cia.vc style messages.
    """
    SERVICE_NAME = 'cia.vc'
    SERVICE_ID = 50

    @classmethod
    def service_description(cls):
        return cls.env().get_template('cia_desc.html').render()

    @classmethod
    def handle_request(cls, user, request, hook, message):
        # Config may not exist for pre-migrate hooks.
        config = hook.config or {}
        # Should we get rid of mIRC colors before sending?
        strip = not config.get('use_colors', True)

        doc = xmltodict.parse(message.encode("utf-8"))
        message = doc['message']
        body = message['body']

        project = message['source']['project']
        branch = message['source'].get('branch')
        module = message['source'].get('module')

        revision = body['commit'].get('revision')
        author = body['commit'].get('author')
        log = body['commit'].get('log')
        url = body['commit'].get('url')
        files = body['commit'].get('files', {}).get('file')

        line = []

        line.append('{RESET}[{BLUE}{name}{RESET}]'.format(
            name=project,
            **HookService.colors
        ))

        if author:
            line.append('{GREEN}{author}{RESET}'.format(
                author=author,
                **HookService.colors
            ))

        if branch:
            line.append('{YELLOW}{branch}{RESET}'.format(
                branch=branch,
                **HookService.colors
            ))

        line.append('*')
        if revision:
            line.append('r{revision}'.format(
                revision=revision
            ))

        if module:
            line.append('{module} /'.format(
                module=module
            ))

        if files:
            line.append('{files} files'.format(
                files=len(files)
            ))

        if log:
            line.append(': {log}'.format(
                log=log
            ))

        yield cls.message(' '.join(line), strip=strip)

    @classmethod
    def form(cls):
        return CIAConfigForm

    @classmethod
    def absolute_url(cls, hook):
        return url_for('hub', key=hook.key, pid=hook.project.id)


@hub.register
def deliver(message):
    """
    A hacky kludge to support cia.vc XML-RPC requests.
    """
    # Must be imported here due to the circular nature of
    # Hook <-> HookService.
    from notifico.models import Hook, Project

    key = request.args.get('key')
    pid = request.args.get('pid')
    if pid:
        try:
            pid = int(pid)
        except ValueError:
            abort(404)

    h = Hook.query.filter_by(key=key, project_id=pid).first()
    if not h:
        return abort(404)

    # Increment the hooks message_count....
    Hook.query.filter_by(id=h.id).update({
        Hook.message_count: Hook.message_count + 1
    })
    # ... and the project-wide message_count.
    Project.query.filter_by(id=h.project.id).update({
        Project.message_count: Project.message_count + 1
    })

    hook = HookService.services.get(h.service_id)
    if hook is None:
        return ''

    hook._request(h.project.owner, request, h, message)
    db.session.commit()
