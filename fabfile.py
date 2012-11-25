# -*- coding: utf8 -*-
import os.path

from fabric import colors
from fabric.api import *
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

    rsync_project(
        remote_dir=www_root(),
        local_dir=os.path.abspath('./utopia')
    )

    with cd(www_root()):
        # Update the SQLAlchemy tables.
        # run('python -m notifico.deploy.build')

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


@roles('web')
def deploy_bots():
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
