# -*- coding: utf8 -*-
import os.path

from fabric import colors
from fabric.api import *
from fabric.utils import puts
from fabric.contrib.project import rsync_project
from fabric.contrib.files import exists


def production():
    """Defaults for deploying to a production server."""
    env.directory = os.path.join('/', 'home', 'notifico')
    env.notifico_dir = os.path.join(env.directory, 'notifico')


def deploy():
    require('directory', provided_by=('production',))
    rsync_project(
        local_dir='./',
        remote_dir=env.notifico_dir,
        exclude=[
            'ENV',
            '*.pyc',
            '.git',
            '*.egg-info',
            'testing.db',
            'local_config.py'
        ]
    )
    with cd(env.notifico_dir):
        run('python setup.py install --user')

        if exists('notifico.pid'):
            run('kill -HUP `cat notifico.pid`')
        else:
            run(' '.join([
                '~/.local/bin/gunicorn',
                '-w 4',
                '-b 127.0.0.1:4000',
                '-p notifico.pid',
                '--daemon',
                '"notifico:create_instance()"'
            ]), pty=False)

        # Try to make sure gunicorn has actually started.
        if exists('notifico.pid'):
            with settings(warn_only=True):
                result = run('kill -0 `cat notifico.pid`')

            if result.failed:
                puts(colors.red('Gunicorn is not running!'))
            else:
                puts(colors.green('Gunicorn started.'))
        else:
            puts(colors.red('Gunicorn is not running!'))


def deploy_bots():
    require('directory', provided_by=('production',))
    with cd(env.notifico_dir):
        run('pip install --user supervisor')
        # Update the supervisord configuration.
        put('misc/deploy/supervisord.conf', 'supervisord.conf')

        if exists('/tmp/supervisord.pid'):
            # Supervisord is already running, so ask it to restart
            # the running bots.
            run('~/.local/bin/supervisorctl restart bots')
        else:
            # ... otherwise, start the daemon with our config file.
            run('~/.local/bin/supervisord -c supervisord.conf')


def css():
    with lcd('notifico/static'):
        local('lessc less/bootstrap.less css/bootstrap.css')
