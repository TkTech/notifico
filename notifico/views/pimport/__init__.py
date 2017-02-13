# -*- coding: utf8 -*-
import urllib
import requests
from itertools import chain

from flask import (
    Blueprint,
    render_template,
    g,
    url_for,
    redirect,
    request,
    current_app
)
import flask_wtf as wtf
from github import Github, GithubException

from notifico import db, user_required
from notifico.models import AuthToken, Project, Hook, Channel

pimport = Blueprint('pimport', __name__, template_folder='templates')


class GithubForm(wtf.Form):
    update_projects = wtf.BooleanField('Update Projects', default=True,
        description=(
            'If a project already exists, update it instead of skipping it.'
    ))
    set_hooks = wtf.BooleanField('Set Hooks', default=False, description=(
        'Sets up each project you select with Github web hooks, so that they'
        ' start recieving commits immediately.'
    ))
    set_commits = wtf.BooleanField('Add to #commits', default=True,
        description=(
            'Sets up public projects you select to broadcast to #commits'
            ' on chat.freenode.net as a default channel (you can always remove'
            ' it later).'
        )
    )


@pimport.route('/github', methods=['GET', 'POST'])
@user_required
def github():
    """
    Import/merge the users existing Github projects, optionally setting up
    web hooks for them.
    """
    if 'code' in request.args:
        # We've finished step one and have a temporary token.
        r = requests.post(
            'https://github.com/login/oauth/access_token',
            params={
                'client_id': current_app.config[
                    'SERVICE_GITHUB_CLIENT_ID'
                ],
                'client_secret': current_app.config[
                    'SERVICE_GITHUB_CLIENT_SECRET'
                ],
                'code': request.args['code']
            },
            headers={
                'Accept': 'application/json'
            }
        )
        result = r.json()
        token = AuthToken.new(result['access_token'], 'github')
        db.session.add(token)
        g.user.tokens.append(token)
        db.session.commit()
        return redirect(url_for('.github'))

    # Check to see if the user has previously authenticated.
    access_token = AuthToken.query.filter_by(
        name='github',
        owner_id=g.user.id
    ).first()

    if access_token is None:
        # The user hasn't setup Github yet, we need to get their OAuth
        # token.
        return redirect(
            'https://github.com/login/oauth/authorize?{0}'.format(
                urllib.urlencode({
                    'client_id': current_app.config[
                        'SERVICE_GITHUB_CLIENT_ID'
                    ],
                    'scope': 'repo'
                })
            )
        )

    # Set authentication and pull a JSON blob of all their
    # repos that they have actually created (or forked).
    # If we leave type as the default ("all") we also get
    # repos they have permission on, which we probably don't want.
    git = Github(
        access_token.token,
        user_agent="Notifico Github Import/0.1"
    )
    # Test to make sure our token is still good...
    try:
        git.get_user().login
    except GithubException as exception:
        # Nope!
        if exception.status == 401:
            # The user almost certainly removed the OAuth token
            # from their github applications page. Remove the now-obsolete
            # token and refresh.
            access_token = AuthToken.query.filter_by(
                name='github',
                owner_id=g.user.id
            ).first()
            if access_token:
                g.user.tokens.remove(access_token)
                db.session.delete(access_token)
                db.session.commit()
            return redirect(request.path)

    user = git.get_user()
    # Get all of the users own repositories
    user_repos = user.get_repos(type='all')
    # ... and get all of the repos in the users organizations ...
    all_repos = chain(user_repos, *[o.get_repos() for o in user.get_orgs()])
    admin_repos = (r for r in all_repos if r.permissions.admin)

    summary = None
    options_form = GithubForm()
    if options_form.validate_on_submit():
        summary = []

        for repo in admin_repos:
            # User didn't check the box, don't import this project.
            # A hack-ish solution to wtform's BooleanField limitation,
            # or I would be using wtf.FieldList(wtf.BooleanField(...)).
            if request.form.get(str(repo.id), None) != 'y':
                continue

            # Make sure this project doesn't already exists.
            p = Project.by_name_and_owner(repo.name, g.user)
            if p is None:
                p = Project.new(
                    repo.name,
                    public=not repo.private,
                    website=repo.homepage
                )
                p.full_name = '{0}/{1}'.format(g.user.username, p.name)
                g.user.projects.append(p)
                db.session.add(p)
                # We need to commit to generate the project.id which is
                # used for the following steps.
                db.session.commit()

                summary.append((
                    'Project {0} created.'.format(repo.name),
                    True
                ))
            elif p is not None and not options_form.update_projects.data:
                summary.append((
                    'Skipping existing project {0}.'.format(repo.name),
                    False
                ))
                continue
            else:
                summary.append((
                    'Project {0} updated.'.format(repo.name),
                    True
                ))

            if options_form.set_hooks.data:
                # The user wanted us to auto-create web hooks for them.
                h = Hook.query.filter_by(
                    project_id=p.id,
                    service_id=10
                ).first()
                if h is None:
                    # No hooks for github have been setup yet, so go ahead
                    # and create one.
                    h = Hook.new(10)
                    p.hooks.append(h)
                    db.session.add(h)

                    repo.create_hook('web', {
                        'url': url_for(
                            'projects.hook_receive',
                            pid=p.id,
                            key=h.key,
                            _external=True
                        )
                    })

            if options_form.set_commits.data and p.public:
                # The user wanted us to add their public projects
                # to #commits@chat.freenode.net for them, but only if it
                # isn't already there.
                c = Channel.query.filter_by(
                    host='chat.freenode.net',
                    channel='#commits',
                    project_id=p.id
                ).first()
                if c is None:
                    # It does *not* already exist, so go ahead and add it.
                    c = Channel.new(
                        '#commits',
                        'chat.freenode.net',
                        6667,
                        ssl=False,
                        public=True
                    )
                    p.channels.append(c)
                    db.session.add(c)

        db.session.commit()

    return render_template(
        'github.html',
        options_form=options_form,
        summary=summary,
        user_repos=admin_repos
    )
