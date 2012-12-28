# -*- coding: utf8 -*-
import os.path

from fabric import colors
from fabric.api import *
from fabric.utils import puts
from fabric.contrib.project import rsync_project
from fabric.contrib.files import exists

# the user used for the server process
env.user = 'tyler'

# the host groups to deploy to
env.roledefs = {
    'web': [
        'n.tkte.ch'
    ]
}


def www_root():
    """
    Returns the directory used to store the frontent project.
    """
    return os.path.abspath(os.path.join(
        '/home',
        env.user
    ))


@roles('web')
def deploy():
    """
    Deploys the notifico project (http).
    """
    # Update the source files.
    rsync_project(
        remote_dir=www_root(),
        local_dir=os.path.abspath('./notifico')
    )

    with cd(www_root()):
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

        # Make sure gunicorn actually started.
        if exists('notifico.pid'):
            with settings(warn_only=True):
                result = run('kill -0 `cat notifico.pid`')

            if result.failed:
                puts(colors.red('Gunicorn is not running!'))
            else:
                puts(colors.green('Gunicorn started.'))
        else:
            puts(colors.red('Gunicorn is not running!'))


@roles('web')
def deploy_bots():
    """
    Deploys the botifico project (irc) and its dependencies.
    """
    with cd(www_root()):
        # Copy over the core IRC library.
        rsync_project(
            remote_dir=www_root(),
            local_dir=os.path.abspath('./utopia')
        )
        # Copy over the Notifico Bot project.
        rsync_project(
            remote_dir=www_root(),
            local_dir=os.path.abspath('./botifico')
        )

        # Update Supervisor's config, which ensures the bots keep running.
        put('misc/deploy/supervisord.conf', 'supervisord.conf')

        # Restart it if it's running, otherwise start it.
        if exists('/tmp/supervisord.pid'):
            run('supervisorctl restart all')
        else:
            run('supervisord -c supervisord.conf')


@roles('web')
def upgrade():
    """
    !DANGER!
    Update alembic and run remotely.
    """
    with cd(www_root()):
        rsync_project(
            remote_dir=www_root(),
            local_dir=os.path.abspath('./alembic')
        )
        put('alembic.ini', 'alembic.ini')
        run('PYTHONPATH=. alembic upgrade head')


@roles('web')
def init():
    """
    Helper to set up a new frontent server.
    """
    # Install the minimum packages for Ubuntu
    sudo('apt-get install build-essential')
    sudo('apt-get install python-dev')
    sudo('apt-get install redis')
    sudo('apt-get install lighttpd')
    sudo('apt-get install python-pip')
    sudo('apt-get install libevent-dev')

    # Install our python dependencies.
    with cd(www_root()):
        p = os.path.join(www_root(), 'misc', 'deploy', 'requirements.txt')
        sudo('pip install --requirement {0}'.format(p))


def css():
    with lcd('notifico/static'):
        local('lessc less/bootstrap.less css/bootstrap.css')
