# -*- coding: utf8 -*-
from fabric import colors
from fabric.api import *
from fabric.utils import abort
from fabric.contrib.project import rsync_project
from fabric.contrib.files import exists


def live():
    """
    Defaults for deploying to a live server.
    """
    env.hosts = ['n.tkte.ch']
    env.user = 'notifico'
    env.ubin = '~/.local/bin'


def bootstrap():
    run('pip install --user supervisor')


def deploy():
    # Since we use the deploying users home folder as the base,
    # we must have it at a minimum.
    require('user', provided_by=['live'])

    # Copy any changes (and only changes) to the server.
    rsync_project(
        local_dir='./',
        remote_dir='notifico',
        exclude=[
            'ENV',
            '*.pyc',
            '.git',
            '*.egg-info',
            'testing.db',
            'local_config.py'
        ]
    )

    with cd('notifico'):
        # Run setup.py to install any new dependencies,
        # or changes to existing dependencies.
        run('python setup.py install --user')
        # Update the supervisord configuration.
        put('misc/deploy/supervisord.conf', 'supervisord.conf')

        # Start or reload supervisord if it's already running.
        with path(env.ubin):
            if exists('supervisord.pid'):
                # Reread the configuration file.
                run('supervisorctl reread')
                # Only reload processes whose configuration has
                # actually been changed.
                run('supervisorctl update')
            else:
                run('supervisord -c supervisord.conf')


def restart_bots():
    require('user', provided_by=['live'])

    with cd('notifico'):
        if not exists('supervisord.pid'):
            abort(colors.red('supervisord is not running!'))
            return

        with path(env.ubin):
            run('supervisorctl restart notifico-bots')


def restart_www():
    require('user', provided_by=['live'])

    with cd('notifico'):
        if not exists('supervisord.pid'):
            abort(colors.red('supervisord is not running!'))
            return

        with path(env.ubin):
            run('supervisorctl restart notifico-www')


def restart_worker():
    require('user', provided_by=['live'])

    with cd('notifico'):
        if not exists('supervisord.pid'):
            abort(colors.red('supervisord is not running!'))
            return

        with path(env.ubin):
            run('supervisorctl restart notifico-worker')
