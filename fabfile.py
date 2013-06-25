# -*- coding: utf8 -*-
import os.path

from fabric import colors
from fabric.api import *
from fabric.utils import puts
from fabric.contrib.project import rsync_project
from fabric.contrib.files import exists


def production():
    """
    Defaults for deploying to a production server.
    """
    env.hosts = ['n.tkte.ch']
    env.user = 'notifico'


def bootstrap():
    run('pip install --user supervisor')


def deploy():
    # Make sure our CSS is up to date.
    with lcd('notifico/static'):
        local('lessc less/bootstrap.less css/bootstrap.css')

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
        if exists('supervisord.pid'):
            run('~/.local/bin/supervisorctl reread')
            run('~/.local/bin/supervisorctl update')
        else:
            run('~/.local/bin/supervisord -c supervisord.conf')


def css():
    with lcd('notifico/static'):
        local('lessc less/bootstrap.less css/bootstrap.css')
