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
from notifico.plugin import get_installed_sources, SourceTypes, SourceForm
from notifico.models.log import Log, LogContext, LogContextType
from notifico.models.group import group_members
from notifico.models.project import Project
from notifico.models.source import Source, SourceInstance, source_groups
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

    query = db.session.query(
        Log
    ).join(
        LogContext
    ).filter(
        LogContext.context_type == LogContextType.PROJECT,
        LogContext.context_id == project.id
    ).order_by(
        Log.created.desc()
    )

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


@projects.route('/<project:project>/source/choose')
def choose_source(project):
    """
    Choose a new source to add to a project.
    """
    crumbs = (
        (project.owner.username, project.owner.dashboard_url),
        (project.name, project.details_url),
        (_('Choose A Source'), None)
    )

    # A messy query, but far more effecient than the 5 joins SQLAlchemy tries
    # to do the "clean" way.  Filters sources to only show those that are
    # allowed to the current user's groups.
    sources = db.session.query(
        Source
    ).join(
        source_groups
    ).join(
        group_members, group_members.c.group_id == source_groups.c.group_id
    ).filter(
        Source.enabled.is_(True),
        group_members.c.user_id == current_user.id
    )

    return render_template(
        'sources/choose.html',
        project=project,
        user=project.owner,
        breadcrumbs=crumbs,
        sources=sources
    )


@projects.route(
    '/<project:project>/source/choose/<int:source_impl>',
    methods=['GET', 'POST']
)
def new_source(project, source_impl):
    """
    Choose a new source to add to a project.
    """
    source_impl = get_installed_sources().get(source_impl)
    if not source_impl:
        abort(404)

    form = source_impl.form()
    if form is None:
        # Some sources may really not have any configuration. In such a
        # case we need a dummy form.
        form = SourceForm()

    if form.validate_on_submit():
        source = SourceInstance(
            config=source_impl.config_from_form(form),
            source_id=source_impl.SOURCE_ID,
            project=project
        )

        db.session.add(source)
        # Flush to populate source.id.
        db.session.flush()
        db.session.add(
            Log.info(
                summary=(
                    'A new %(source_name)s source was created by %(user)s.'
                ),
                payload={
                    'source_name': source_impl.SOURCE_NAME,
                    'user': current_user.username,
                    'user_id': current_user.id
                },
                related=[
                    LogContext(
                        context_type=LogContextType.USER,
                        context_id=current_user.id
                    ),
                    LogContext(
                        context_type=LogContextType.PROJECT,
                        context_id=project.id
                    ),
                    LogContext(
                        context_type=LogContextType.SOURCE_IMPL,
                        context_id=source_impl.SOURCE_ID
                    ),
                    LogContext(
                        context_type=LogContextType.SOURCE_INST,
                        context_id=source.id
                    )
                ]
            )
        )
        db.session.commit()

        # For webhook-type sources, we want the chance to present the
        # hook front-and-center with instructions on how to use it.
        if source_impl.SOURCE_TYPE == SourceTypes.WEBHOOK:
            return redirect(
                url_for(
                    '.get_source_url',
                    project=project,
                    source=source.id
                )
            )

        flash(_('Your source has been created.'), category='success')
        return redirect(project.details_url)
    else:
        crumbs = (
            (project.owner.username, project.owner.dashboard_url),
            (project.name, project.details_url),
            (_('Choose A Source'), project.choose_source_url),
            (source_impl.SOURCE_NAME, None),
        )

        return render_template(
            'sources/new.html',
            project=project,
            user=project.owner,
            breadcrumbs=crumbs,
            source=source_impl,
            form=form
        )


@projects.route('/<project:project>/source/<int:source>')
def get_source_url(project, source):
    """Presents the user with the webhook URL for the given source.
    """
    source = SourceInstance.query.get_or_404(source)

    return render_template(
        'sources/get_url.html',
        project=project,
        user=project.owner,
        source=source
    )


@projects.route(
    '/<project:project>/source/<int:source>/edit',
    methods=['GET', 'POST']
)
def edit_source(project, source):
    """Edit an existing source."""
    source = SourceInstance.query.get_or_404(source)

    crumbs = (
        (project.owner.username, project.owner.dashboard_url),
        (project.name, project.details_url),
        (source.impl.SOURCE_NAME, None),
    )

    form = source.impl.form()
    if form is None:
        # Some sources may really not have any configuration. In such a
        # case we need a dummy form.
        form = SourceForm()

    if request.method == 'GET':
        source.impl.update_form_with_config(form, source.config)

    if form.validate_on_submit():
        source.config = source.impl.config_from_form(form)

        db.session.add(source)
        db.session.commit()

        flash(_('Your source has been updated.'), category='success')
        return redirect(project.details_url)

    return render_template(
        'sources/edit.html',
        project=project,
        user=project.owner,
        breadcrumbs=crumbs,
        source=source.impl,
        form=form
    )