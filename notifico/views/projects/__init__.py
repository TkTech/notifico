from functools import wraps

from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    url_for,
    abort,
    request
)
import flask_wtf as wtf
from flask_babel import lazy_gettext as _
from wtforms import fields, validators

from notifico import db, user_required
from notifico.models.user import User
from notifico.models.project import Project

projects = Blueprint('projects', __name__, template_folder='templates')


class ProjectDetailsForm(wtf.FlaskForm):
    name = fields.StringField('Project Name', validators=[
        validators.DataRequired(),
        validators.Length(1, 50),
        validators.Regexp(r'^[a-zA-Z0-9_\-\.]*$', message=(
            'Project name must only contain a to z, 0 to 9, dashes'
            ' and underscores.'
        ))
    ])
    public = fields.BooleanField(
        'Public',
        default=True,
        description=_(
            'If your project is public, other users will be able to see it'
            ' exists. However, you can still make your channels individually'
            ' public or private.'
        )
    )
    website = fields.StringField('Project URL', validators=[
        validators.Optional(),
        validators.Length(max=1024),
        validators.URL()
    ])


class HookDetailsForm(wtf.FlaskForm):
    service_id = fields.SelectField('Service', validators=[
        validators.DataRequired()
    ], coerce=int)


class PasswordConfirmForm(wtf.FlaskForm):
    password = fields.PasswordField('Password', validators=[
        validators.DataRequired()
    ])

    def validate_password(form, field):
        if not User.login(g.user.username, field.data):
            raise validators.ValidationError('Your password is incorrect.')


class ChannelDetailsForm(wtf.FlaskForm):
    channel = fields.StringField('Channel', validators=[
        validators.DataRequired(),
        validators.Length(min=1, max=80)
    ])
    host = fields.StringField('Host', validators=[
        validators.DataRequired(),
        validators.Length(min=1, max=255)
    ], default='chat.freenode.net')
    port = fields.IntegerField('Port', validators=[
        validators.NumberRange(1024, 66552)
    ], default=6667)
    ssl = fields.BooleanField('Use SSL', default=False)
    public = fields.BooleanField('Public', default=True, description=(
        'Allow others to see that this channel exists.'
    ))


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
        projects=projects,
        page_title='Notifico! - {u.username}\'s Projects'.format(
            u=u
        )
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
    return render_template(
        'project_details.html',
        project=p,
        user=u,
        page_title='Notifico! - {u.username}/{p.name}'.format(
            u=u,
            p=p
        )
    )
