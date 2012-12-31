# -*- coding: utf8 -*-
import os.path
from contextlib import contextmanager as _contextmanager

from fabric import colors
from fabric.api import *
from fabric.utils import puts
from fabric.contrib.project import rsync_project
from fabric.contrib.files import exists


@_contextmanager
def virtualenv():
    with cd(env.directory):
        with prefix(env.activate):
            yield


def production():
    """Defaults for deploying to a production server."""
    env.directory = os.path.join('/', 'home', env.user, 'notifico2')
    env.activate = 'source {path}'.format(
        path=os.path.join(env.directory, 'ENV', 'bin', 'activate')
    )
    env.notifico_dir = os.path.join(env.directory, 'notifico')


def ve_create():
    """
    Create a new virtualenv directory on the server.
    """
    require('directory', provided_by=('production',))
    run('virtualenv {args} {path}'.format(
        args=' '.join((
            '--clear',      # Start from scratch
            '--distribute'  # Use distribute instead of setuptools
        )),
        path=os.path.join(env.directory, 'ENV')
    ))


def ve_list():
    """
    Get the list of currently installed packages in the remote virtualenv.
    """
    with virtualenv():
        run('pip freeze')


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
    with virtualenv():
        with cd(env.notifico_dir):
            run('python setup.py install')

            if exists('notifico.pid'):
                run('kill -HUP `cat notifico.pid`')
            else:
                run(' '.join([
                    'gunicorn',
                    '-w 4',
                    '-b 127.0.0.1:4000',
                    '-p notifico.pid',
                    '--daemon',
                     '"notifico:start(debug=False)"'
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
    with virtualenv():
        with cd(env.directory):
            run('pip install supervisor')
            # Update the supervisord configuration.
            put('misc/deploy/supervisord.conf', 'supervisord.conf')
            put('misc/deploy/run_bots.sh', 'run_bots.sh')

            if exists('/tmp/supervisord.pid'):
                # Supervisord is already running, so ask it to restart
                # the running bots.
                run('supervisorctl restart bots')
            else:
                # ... otherwise, start the daemon with our config file.
                run('supervisord -c supervisord.conf')


def upgrade_utopia():
    require('directory', provided_by=('production',))
    with virtualenv():
        with cd(env.directory):
            run(
                'pip install'
                ' https://github.com/TkTech/utopia/tarball/'
                'master#egg=UtopiaIRC --upgrade'
            )


def css():
    with lcd('notifico/static'):
        local('lessc less/custom.less css/custom.css')
