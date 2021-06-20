from functools import wraps

from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    url_for,
    abort,
    request,
    flash
)
import flask_wtf as wtf
from flask_babel import lazy_gettext as _

from notifico import db, user_required
from notifico.provider import get_providers, ProviderTypes
from notifico.models.user import User
from notifico.models.project import Project
from notifico.models.provider import Provider
from notifico.views.projects.forms import (
    ProjectDetailsForm
)

projects = Blueprint('projects', __name__, template_folder='templates')


def project_action(f):
    """
    A decorator for views which act on a project. The function
    should take two kwargs, `u` (the username) and `p` (the project name),
    which will be resolved and replaced, or a 404 will be raised if either
    could not be found.
    """
    @wraps(f)
    def _wrapped(*args, **kwargs):
        u = User.by_username(kwargs.pop('u'))
        if not u:
            # No such user exists.
            return abort(404)

        p = Project.by_name_and_owner(kwargs.pop('p'), u)
        if not p:
            # Project doesn't exist (404 Not Found)
            return abort(404)

        kwargs['p'] = p
        kwargs['u'] = u

        return f(*args, **kwargs)
    return _wrapped


@projects.route('/<u>/')
def dashboard(u):
    """
    Display an overview of all the user's projects with summary
    statistics.
    """
    u = User.by_username(u)
    if not u:
        # No such user exists.
        return abort(404)

    is_owner = (g.user and g.user.id == u.id)

    # Get all projects by decending creation date.
    projects = (
        u.projects
        .order_by(False)
        .order_by(Project.created.desc())
    )
    if not is_owner:
        # If this isn't the users own page, only
        # display public projects.
        projects = projects.filter_by(public=True)

    return render_template(
        'dashboard.html',
        user=u,
        is_owner=is_owner,
        projects=projects
    )


@projects.route('/new', methods=['GET', 'POST'])
@user_required
def new():
    """
    Create a new project.
    """
    form = ProjectDetailsForm()
    if form.validate_on_submit():
        p = Project.by_name_and_owner(form.name.data, g.user)
        if p:
            form.name.errors = [
                wtf.ValidationError('Project name must be unique.')
            ]
        else:
            p = Project.new(
                form.name.data,
                public=form.public.data,
                website=form.website.data
            )
            p.full_name = '{0}/{1}'.format(g.user.username, p.name)
            g.user.projects.append(p)
            db.session.add(p)

            db.session.commit()

            return redirect(url_for('.details', u=g.user.username, p=p.name))

    return render_template('new_project.html', form=form)


@projects.route('/<u>/<p>/edit', methods=['GET', 'POST'])
@user_required
@project_action
def edit_project(u, p):
    """
    Edit an existing project.
    """
    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    form = ProjectDetailsForm(obj=p)
    if form.validate_on_submit():
        old_p = Project.by_name_and_owner(form.name.data, g.user)
        if old_p and old_p.id != p.id:
            form.name.errors = [
                wtf.ValidationError('Project name must be unique.')
            ]
        else:
            p.name = form.name.data
            p.website = form.website.data
            p.public = form.public.data
            p.full_name = '{0}/{1}'.format(g.user.username, p.name)
            db.session.commit()
            return redirect(url_for('.dashboard', u=u.username))

    return render_template(
        'edit_project.html',
        project=p,
        form=form
    )


@projects.route('/<u>/<p>/delete', methods=['GET', 'POST'])
@user_required
@project_action
def delete_project(u, p):
    """
    Delete an existing project.
    """
    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    if request.method == 'POST' and request.form.get('do') == 'd':
        db.session.delete(p)
        db.session.commit()
        return redirect(url_for('.dashboard', u=u.username))

    return render_template('delete_project.html', project=p)


@projects.route('/<u>/<p>')
@project_action
def details(u, p):
    """
    Show the details for an existing project.
    """
    crumbs = (
        (u.username, url_for('.dashboard', u=u.username)),
        (p.name, None)
    )

    return render_template(
        'project_details.html',
        project=p,
        user=u,
        breadcrumbs=crumbs
    )


@projects.route('/<u>/<p>/provider/choose')
@project_action
def choose_provider(u, p):
    """
    Choose a new provider to add to a project.
    """
    crumbs = (
        (u.username, url_for('.dashboard', u=u.username)),
        (p.name, p.details_url),
        (_('Choose A Provider'), None)
    )

    providers = get_providers()

    return render_template(
        'choose_provider.html',
        project=p,
        user=u,
        breadcrumbs=crumbs,
        providers=providers.values()
    )


@projects.route(
    '/<u>/<p>/provider/choose/<int:provider>',
    methods=['GET', 'POST']
)
@project_action
def new_provider(u, p, provider):
    """
    Choose a new provider to add to a project.
    """
    provider = get_providers()[provider]

    form = provider.form()
    if form is None:
        # Some providers may really not have any configuration. In such a
        # case we need a dummy form.
        form = wtf.FlaskForm()

    if form.validate_on_submit():
        stored_provider = Provider(
            config=provider.config_from_form(form),
            provider_id=provider.PROVIDER_ID,
            project=p
        )

        db.session.add(stored_provider)
        # TODO: Although incredibly unlikely, there's a chance for a conflict
        # here if the randomly generated key collides. Should handle it.
        db.session.commit()

        # For webhook-type providers, we want the chance to present the
        # hook front-and-center with instructions on how to use it.
        if provider.PROVIDER_TYPE == ProviderTypes.WEBHOOK:
            crumbs = (
                (u.username, url_for('.dashboard', u=u.username)),
                (p.name, p.details_url),
                (_('Choose A Provider'), p.choose_provider_url),
                (provider.PROVIDER_NAME, None),
                (_('Install Webhook'), None)
            )

            return render_template(
                'post_new_provider.html',
                project=p,
                user=u,
                breadcrumbs=crumbs,
                provider=provider,
                stored_provider=stored_provider,
                form=form
            )

        flash(_('Your provider has been created!'), category='success')
        return redirect(p.details_url)
    else:
        crumbs = (
            (u.username, url_for('.dashboard', u=u.username)),
            (p.name, p.details_url),
            (_('Choose A Provider'), p.choose_provider_url),
            (provider.PROVIDER_NAME, None),
        )

        return render_template(
            'new_provider.html',
            project=p,
            user=u,
            breadcrumbs=crumbs,
            provider=provider,
            form=form
        )
