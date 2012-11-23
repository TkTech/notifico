from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    flash,
    url_for,
    abort,
    request
)
from flask.ext import wtf

from frontend import user_required
from frontend.models import User, Project, Hook
from frontend.services import registered_services

projects = Blueprint('projects', __name__, template_folder='templates')


class ProjectDetailsForm(wtf.Form):
    name = wtf.TextField('Project Name', validators=[
        wtf.Required(),
        wtf.Length(2, 50)
    ])
    public = wtf.BooleanField('Public', validators=[
    ], default=True)
    website = wtf.TextField('Project URL', validators=[
        wtf.Optional(),
        wtf.Length(max=1024),
        wtf.validators.URL()
    ])

    def validate_name(form, field):
        p = Project.by_name_and_owner(field.data, g.user)
        if p:
            raise wtf.ValidationError('Project name must be unique.')


class HookDetailsForm(wtf.Form):
    service_id = wtf.SelectField('Service', validators=[
        wtf.Required()
    ], coerce=int)


class PasswordConfirmForm(wtf.Form):
    password = wtf.PasswordField('Password', validators=[
        wtf.Required()
    ])

    def validate_password(form, field):
        if not User.login(g.user.username, field.data):
            raise wtf.ValidationError('Your password is incorrect.')


@projects.route('/')
@user_required
def overview():
    """
    Display an overview of all the user's projects with summary
    statistics.
    """
    g.add_breadcrumb('Projects', url_for('.overview'))
    return render_template('overview.html')


@projects.route('/new', methods=['GET', 'POST'])
@user_required
def new():
    """
    Create a new project.
    """
    g.add_breadcrumb('New Project', url_for('.new'))
    form = ProjectDetailsForm()
    if form.validate_on_submit():
        p = Project.new(
            form.name.data,
            public=form.public.data,
            website=form.website.data
        )
        p.full_name = '{0}/{1}'.format(g.user.username, p.name)
        g.db.session.add(p)
        g.user.projects.append(p)
        g.db.session.commit()
        flash('Your project has been created.', 'success')
        return redirect(url_for('.overview'))

    return render_template('new_project.html', form=form)


@projects.route('/edit/<int:pid>', methods=['GET', 'POST'])
@user_required
def edit_project(pid):
    """
    Edit an existing project.
    """
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    form = ProjectDetailsForm(obj=p)
    if form.validate_on_submit():
        p.website = form.website.data
        p.public = form.public.data
        g.db.session.commit()
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('.overview'))

    return render_template('edit_project.html',
        project=p,
        form=form
    )


@projects.route('/delete/<int:pid>', methods=['GET', 'POST'])
@user_required
def delete_project(pid):
    """
    Delete an existing project.
    """
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    form = PasswordConfirmForm()
    if form.validate_on_submit():
        g.db.session.delete(p)
        g.db.session.commit()
        flash('Your project has been deleted.', 'success')
        return redirect(url_for('.overview'))

    return render_template('delete_project.html',
        project=p,
        form=form
    )


@projects.route('/<int:pid>')
def details(pid):
    """
    Show an existing project's details.
    """
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (Not Found)
        return abort(404)
    elif not p.public and not g.user:
        # Not public and no logged in user. (Forbidden)
        return abort(403)
    elif not p.public and p.owner.id != g.user.id:
        # Not public and not owner. (Forbidden)
        return abort(403)

    is_owner = (g.user and g.user.id == p.owner_id)

    return render_template('project_details.html',
        project=p,
        is_owner=is_owner
    )


@projects.route('/hook/new/<int:pid>')
@user_required
def new_hook(pid):
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    form = HookDetailsForm()
    form.service_id.choices = [
        (k, s.service_name()) for k, s in registered_services().items()
    ]
    if form.validate_on_submit():
        pass

    return render_template('new_hook.html',
        project=p,
        form=form
    )


@projects.route('/h/<int:pid>/<key>', methods=['POST'])
def hook_recieve(pid, key):
    pass


@projects.route('/hook/delete/<int:pid>/<int:hid>', methods=['GET', 'POST'])
@user_required
def delete_hook(pid, hid):
    """
    Delete an existing service hook.
    """
    p = Project.query.get(pid)
    h = Hook.query.get(hid)
    if not p or not h:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if p.owner.id != g.user.id or h.project.id != p.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    if request.method == 'POST' and request.form.get('do') == 'd':
        p.hooks.remove(h)
        g.db.session.delete(h)
        g.db.session.commit()
        flash('The hook has been deleted.', 'success')
        return redirect(url_for('.details', pid=pid))

    return render_template('delete_hook.html',
        project=p,
        hook=h
    )
