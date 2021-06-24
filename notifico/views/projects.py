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
from flask_login import login_required, current_user

from notifico import db
from notifico.provider import get_providers, ProviderTypes, ProviderForm
from notifico.models.user import User
from notifico.models.project import Project
from notifico.models.provider import Provider
from notifico.forms.projects import ProjectDetailsForm

projects = Blueprint('projects', __name__)


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

    # Get all projects by decending creation date.
    projects = (
        u.projects
        .order_by(False)
        .order_by(Project.created.desc())
    )

    return render_template(
        'projects/dashboard.html',
        user=u,
        projects=projects
    )


@projects.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """
    Create a new project.
    """
    form = ProjectDetailsForm()
    if form.validate_on_submit():
        p = Project.by_name_and_owner(form.name.data, current_user)
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
            p.full_name = '{0}/{1}'.format(current_user.username, p.name)
            current_user.projects.append(p)

            db.session.add(p)
            db.session.commit()

            return redirect(
                url_for(
                    '.details',
                    u=current_user.username,
                    p=p.name
                )
            )

    return render_template('projects/new.html', form=form, user=current_user)


@projects.route('/<u>/<p>/edit', methods=['GET', 'POST'])
@login_required
@project_action
def edit_project(u, p):
    """
    Edit an existing project.
    """
    form = ProjectDetailsForm(obj=p)
    if form.validate_on_submit():
        old_p = Project.by_name_and_owner(form.name.data, current_user)
        if old_p and old_p.id != p.id:
            form.name.errors = [
                wtf.ValidationError('Project name must be unique.')
            ]
        else:
            p.name = form.name.data
            p.website = form.website.data
            p.public = form.public.data
            p.full_name = '{0}/{1}'.format(current_user.username, p.name)
            db.session.commit()
            return redirect(url_for('.dashboard', u=u.username))

    return render_template(
        'projects/edit.html',
        project=p,
        form=form
    )


@projects.route('/<u>/<p>/delete', methods=['GET', 'POST'])
@login_required
@project_action
def delete_project(u, p):
    """
    Delete an existing project.
    """
    if request.method == 'POST' and request.form.get('do') == 'd':
        db.session.delete(p)
        db.session.commit()
        return redirect(u.dashboard_url)

    return render_template(
        'projects/delete.html',
        project=p,
        user=u
    )


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
        'projects/get.html',
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
        'providers/choose.html',
        project=p,
        user=u,
        breadcrumbs=crumbs,
        providers=providers.values()
    )


@projects.route(
    '/<u>/<p>/provider/choose/<int:provider_impl>',
    methods=['GET', 'POST']
)
@project_action
def new_provider(u, p, provider_impl):
    """
    Choose a new provider to add to a project.
    """
    provider_impl = get_providers().get(provider_impl)
    if not provider_impl:
        abort(404)

    form = provider_impl.form()
    if form is None:
        # Some providers may really not have any configuration. In such a
        # case we need a dummy form.
        form = ProviderForm()

    if form.validate_on_submit():
        provider = Provider(
            config=provider_impl.config_from_form(form),
            provider_id=provider_impl.PROVIDER_ID,
            provider_type=provider_impl.PROVIDER_TYPE,
            project=p
        )

        db.session.add(provider)
        # TODO: Although incredibly unlikely, there's a chance for a conflict
        # here if the randomly generated key collides. Should handle it.
        db.session.commit()

        # For webhook-type providers, we want the chance to present the
        # hook front-and-center with instructions on how to use it.
        if provider_impl.PROVIDER_TYPE == ProviderTypes.WEBHOOK:
            return redirect(
                url_for(
                    '.get_provider_url',
                    p=p.name,
                    u=u.username,
                    provider=provider.id
                )
            )

        flash(_('Your provider has been created.'), category='success')
        return redirect(p.details_url)
    else:
        crumbs = (
            (u.username, url_for('.dashboard', u=u.username)),
            (p.name, p.details_url),
            (_('Choose A Provider'), p.choose_provider_url),
            (provider_impl.PROVIDER_NAME, None),
        )

        return render_template(
            'providers/new.html',
            project=p,
            user=u,
            breadcrumbs=crumbs,
            provider=provider_impl,
            form=form
        )


@projects.route('/<u>/<p>/provider/<int:provider>')
@project_action
def get_provider_url(u, p, provider):
    """Presents the user with the webhook URL for the given provider.
    """
    provider = Provider.query.get_or_404(provider)

    return render_template(
        'providers/get_url.html',
        project=p,
        user=u,
        provider=provider
    )


@projects.route(
    '/<u>/<p>/provider/<int:provider>/edit',
    methods=['GET', 'POST']
)
@project_action
def edit_provider(u, p, provider):
    """Edit an existing provider."""
    provider = Provider.query.get_or_404(provider)

    crumbs = (
        (u.username, url_for('.dashboard', u=u.username)),
        (p.name, p.details_url),
        (provider.p.PROVIDER_NAME, None),
    )

    form = provider.p.form()
    if form is None:
        # Some providers may really not have any configuration. In such a
        # case we need a dummy form.
        form = ProviderForm()

    provider.p.update_form_with_config(form, provider.config)

    if form.validate_on_submit():
        provider.config = provider.p.config_from_form(form)
        db.session.add(provider)
        db.session.commit()

        flash(_('Your provider has been updated.'), category='success')
        return redirect(p.details_url)

    return render_template(
        'providers/edit.html',
        project=p,
        user=u,
        breadcrumbs=crumbs,
        provider=provider.p,
        form=form
    )
