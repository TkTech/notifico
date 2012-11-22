from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    flash,
    url_for,
    abort
)
from flask.ext import wtf

from frontend import user_required
from frontend.models import User, Project

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
    return render_template('overview.html')


@projects.route('/new', methods=['GET', 'POST'])
@user_required
def new():
    form = ProjectDetailsForm()
    if form.validate_on_submit():
        p = Project.new(
            form.name.data,
            public=form.public.data,
            website=form.website.data
        )
        g.db.session.add(p)
        g.user.projects.append(p)
        g.db.session.commit()
        flash('Your project has been created.', 'success')
        return redirect(url_for('.overview'))

    return render_template('new_project.html', form=form)


@projects.route('/edit/<int:pid>', methods=['GET', 'POST'])
@user_required
def edit_project(pid):
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if not p.public and p.owner.id != g.user.id:
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
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if not p.public and p.owner.id != g.user.id:
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
@user_required
def details(pid):
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if not p.public and p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    is_owner = (g.user and g.user.id == p.owner_id)

    return render_template('project_details.html',
        project=p,
        is_owner=is_owner
    )
