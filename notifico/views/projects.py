from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    abort,
    request,
    flash
)
from wtforms import ValidationError
from flask_babel import lazy_gettext as _
from flask_login import login_required, current_user

from notifico.extensions import db
from notifico.provider import get_providers, ProviderTypes, ProviderForm
from notifico.models.log import Log
from notifico.models.project import Project
from notifico.models.provider import Provider
from notifico.forms.projects import ProjectDetailsForm

projects = Blueprint('projects', __name__)


@projects.route('/<user:user>/')
def dashboard(user):
    """
    Display an overview of all the user's projects with summary
    statistics.
    """
    # Get all projects by decending creation date.
    projects = (
        user.projects
        .order_by(False)
        .order_by(Project.created.desc())
    )

    return render_template(
        'projects/dashboard.html',
        user=user,
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
        exists = db.session.query(
            Project.query.filter(
                Project.name_i == form.name.data,
                Project.owner == current_user
            ).exists()
        ).scalar()

        if exists:
            form.name.errors = [
                ValidationError(_('Project name must be unique.'))
            ]
        else:
            p = Project(
                name=form.name.data,
                website=form.website.data,
                public=form.public.data
            )
            current_user.projects.append(p)

            db.session.add(p)
            db.session.commit()

            return redirect(p.details_url)

    return render_template('projects/new.html', form=form, user=current_user)


@projects.route('/<project:project>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project):
    """
    Edit an existing project.
    """
    form = ProjectDetailsForm(obj=project)
    if form.validate_on_submit():
        exists = db.session.query(
            Project.query.filter(
                Project.name_i == form.name.data,
                Project.owner == current_user,
                # We want to see if were taking the name from another project,
                # not ourselves.
                Project.id != project.id,
            ).exists()
        ).scalar()

        if exists:
            form.name.errors = [
                ValidationError(_('Project name must be unique.'))
            ]
        else:
            project.name = form.name.data
            project.public = form.public.data

            db.session.add(project)
            db.session.commit()

            return redirect(project.owner.dashboard_url)

    return render_template(
        'projects/edit.html',
        project=project,
        form=form
    )


@projects.route('/<project:project>/delete', methods=['GET', 'POST'])
@login_required
def delete_project(project):
    """
    Delete an existing project.
    """
    if request.method == 'POST':
        redirect_to = project.owner.dashboard_url
        db.session.delete(project)
        db.session.commit()
        return redirect(redirect_to)

    return render_template(
        'projects/delete.html',
        project=project,
        user=project.owner
    )


@projects.route('/<project:project>/')
def details(project):
    """
    Show the details for an existing project.
    """
    crumbs = (
        (project.owner.username, project.owner.dashboard_url),
        (project.name, None)
    )

    # This will become a performanc pain point very quickly. Needs to be
    # moved to sort-pagination off of the timestamp.
    query = project.logs.order_by(Log.created.desc())
    logs = query.paginate(
        page=1,
        per_page=25,
        max_per_page=25
    )

    return render_template(
        'projects/get.html',
        project=project,
        user=project.owner,
        breadcrumbs=crumbs,
        project_logs=logs
    )


@projects.route('/<project:project>/provider/choose')
def choose_provider(project):
    """
    Choose a new provider to add to a project.
    """
    crumbs = (
        (project.owner.username, project.owner.dashboard_url),
        (project.name, project.details_url),
        (_('Choose A Provider'), None)
    )

    providers = get_providers()

    return render_template(
        'providers/choose.html',
        project=project,
        user=project.owner,
        breadcrumbs=crumbs,
        providers=providers.values()
    )


@projects.route(
    '/<project:project>/provider/choose/<int:provider_impl>',
    methods=['GET', 'POST']
)
def new_provider(project, provider_impl):
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
            project=project
        )

        project.logs.append(Log.info(
            summary=(
                'A new %(provider_name)s provider was created by %(user)s.'
            ),
            payload={
                'provider_name': provider_impl.PROVIDER_NAME,
                'user': current_user.username,
                'user_id': current_user.id
            }
        ))

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
                    project=project,
                    provider=provider.id
                )
            )

        flash(_('Your provider has been created.'), category='success')
        return redirect(project.details_url)
    else:
        crumbs = (
            (project.owner.username, project.owner.dashboard_url),
            (project.name, project.details_url),
            (_('Choose A Provider'), project.choose_provider_url),
            (provider_impl.PROVIDER_NAME, None),
        )

        return render_template(
            'providers/new.html',
            project=project,
            user=project.owner,
            breadcrumbs=crumbs,
            provider=provider_impl,
            form=form
        )


@projects.route('/<project:project>/provider/<int:provider>')
def get_provider_url(project, provider):
    """Presents the user with the webhook URL for the given provider.
    """
    provider = Provider.query.get_or_404(provider)

    return render_template(
        'providers/get_url.html',
        project=project,
        user=project.owner,
        provider=provider
    )


@projects.route(
    '/<project:project>/provider/<int:provider>/edit',
    methods=['GET', 'POST']
)
def edit_provider(project, provider):
    """Edit an existing provider."""
    provider = Provider.query.get_or_404(provider)

    crumbs = (
        (project.owner.username, project.owner.dashboard_url),
        (project.name, project.details_url),
        (provider.p.PROVIDER_NAME, None),
    )

    form = provider.p.form()
    if form is None:
        # Some providers may really not have any configuration. In such a
        # case we need a dummy form.
        form = ProviderForm()

    if request.method == 'GET':
        provider.p.update_form_with_config(form, provider.config)

    if form.validate_on_submit():
        provider.config = provider.p.config_from_form(form)

        db.session.add(provider)
        db.session.commit()

        flash(_('Your provider has been updated.'), category='success')
        return redirect(project.details_url)

    return render_template(
        'providers/edit.html',
        project=project,
        user=project.owner,
        breadcrumbs=crumbs,
        provider=provider.p,
        form=form
    )
