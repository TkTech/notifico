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
from wtforms import fields, validators

from notifico import db, user_required
from notifico.models import User, Project, Hook, Channel
from notifico.service import available_services

projects = Blueprint('projects', __name__, template_folder='templates')


class ProjectDetailsForm(wtf.FlaskForm):
    name = fields.StringField('Project Name', validators=[
        validators.InputRequired(),
        validators.Length(1, 50),
        validators.Regexp(r'^[a-zA-Z0-9_\-\.]*$', message=(
            'Project name must only contain a to z, 0 to 9, dashes'
            ' and underscores.'
        ))
    ])
    public = fields.BooleanField('Public', default=True)
    website = fields.StringField('Project URL', validators=[
        validators.Optional(),
        validators.Length(max=1024),
        validators.URL()
    ])


class HookDetailsForm(wtf.FlaskForm):
    service_id = fields.SelectField('Service', validators=[
        validators.InputRequired()
    ], coerce=int)


class PasswordConfirmForm(wtf.FlaskForm):
    password = fields.PasswordField('Password', validators=[
        validators.InputRequired()
    ])

    def validate_password(form, field):
        if not User.login(g.user.username, field.data):
            raise validators.ValidationError('Your password is incorrect.')


class ChannelDetailsForm(wtf.FlaskForm):
    channel = fields.StringField('Channel', validators=[
        validators.InputRequired(),
        validators.Length(min=1, max=80)
    ])
    host = fields.StringField('Host', validators=[
        validators.InputRequired(),
        validators.Length(min=1, max=255)
    ], default='irc.libera.chat')
    port = fields.IntegerField('Port', validators=[
        validators.NumberRange(1024, 66552)
    ], default=6697)
    ssl = fields.BooleanField('Use SSL', default=True)
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

    return render_template('dashboard.html',
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

            if p.public:
                # New public projects get added to #commits by default.
                c = Channel.new(
                    '#commits',
                    'irc.libera.chat',
                    6697,
                    ssl=True,
                    public=True
                )
                p.channels.append(c)

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

    return render_template('edit_project.html',
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
    if not p.can_see(g.user):
        return redirect(url_for('public.landing'))

    can_modify = p.can_modify(g.user)

    visible_channels = p.channels
    if not can_modify:
        visible_channels = visible_channels.filter_by(public=True)

    return render_template(
        'project_details.html',
        project=p,
        user=u,
        visible_channels=visible_channels,
        can_modify=can_modify,
        page_title='Notifico! - {u.username}/{p.name}'.format(
            u=u,
            p=p
        )
    )


@projects.route('/<u>/<p>/hook/new', defaults={'sid': 10}, methods=[
    'GET', 'POST'])
@projects.route('/<u>/<p>/hook/new/<int:sid>', methods=['GET', 'POST'])
@user_required
@project_action
def new_hook(u, p, sid):
    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    hook = available_services()[sid]
    form = hook.form()
    if form:
        form = form()

    if form and hook.validate(form, request):
        h = Hook.new(sid, config=hook.pack_form(form))
        p.hooks.append(h)
        db.session.add(h)
        db.session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form is None and request.method == 'POST':
        h = Hook.new(sid)
        p.hooks.append(h)
        db.session.add(h)
        db.session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))

    return render_template('new_hook.html',
        project=p,
        services=available_services(),
        service=hook,
        form=form
    )


@projects.route('/<u>/<p>/hook/edit/<int:hid>', methods=['GET', 'POST'])
@user_required
@project_action
def edit_hook(u, p, hid):
    if p.owner.id != g.user.id:
        return abort(403)

    h = Hook.query.get(hid)
    if h is None:
        # You can't edit a hook that doesn't exist!
        return abort(404)

    if h.project.owner.id != g.user.id:
        # You can't edit a hook that isn't yours!
        return abort(403)

    hook_service = h.hook()
    form = hook_service.form()
    if form:
        form = form()

    if form and hook_service.validate(form, request):
        h.config = hook_service.pack_form(form)
        db.session.add(h)
        db.session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form is None and request.method == 'POST':
        db.session.add(h)
        db.session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form:
        hook_service.load_form(form, h.config)

    return render_template('edit_hook.html',
        project=p,
        services=available_services(),
        service=hook_service,
        form=form
    )


@projects.route('/h/<int:pid>/<key>', methods=['GET', 'POST'])
def hook_receive(pid, key):
    h = Hook.query.filter_by(key=key, project_id=pid).first()
    if not h or not h.project:
        # The hook being pushed to doesn't exist, has been deleted,
        # or is a leftover from a project cull (which destroyed the project
        # but not the hooks associated with it).
        return abort(404)

    # Increment the hooks message_count....
    Hook.query.filter_by(id=h.id).update({
        Hook.message_count: Hook.message_count + 1
    })
    # ... and the project-wide message_count.
    Project.query.filter_by(id=h.project.id).update({
        Project.message_count: Project.message_count + 1
    })

    hook = available_services()[h.service_id]
    if hook is None:
        # TODO: This should be logged somewhere.
        return ''

    hook._request(h.project.owner, request, h)

    db.session.commit()
    return ''


@projects.route('/<u>/<p>/hook/delete/<int:hid>', methods=['GET', 'POST'])
@user_required
@project_action
def delete_hook(u, p, hid):
    """
    Delete an existing service hook.
    """
    h = Hook.query.get(hid)
    if not h:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if p.owner.id != g.user.id or h.project.id != p.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    if request.method == 'POST' and request.form.get('do') == 'd':
        p.hooks.remove(h)
        db.session.delete(h)
        db.session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))

    return render_template('delete_hook.html',
        project=p,
        hook=h
    )


@projects.route('/<u>/<p>/channel/new', methods=['GET', 'POST'])
@user_required
@project_action
def new_channel(u, p):
    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    form = ChannelDetailsForm()
    if form.validate_on_submit():
        host = form.host.data.strip().lower()
        channel = form.channel.data.strip().lower()

        # Make sure this isn't a duplicate channel before we create it.
        c = Channel.query.filter_by(
            host=host,
            channel=channel,
            project_id=p.id
        ).first()
        if not c:
            c = Channel.new(
                channel,
                host,
                port=form.port.data,
                ssl=form.ssl.data,
                public=form.public.data
            )
            p.channels.append(c)
            db.session.add(c)
            db.session.commit()
            return redirect(url_for('.details', p=p.name, u=u.username))
        else:
            form.channel.errors = [wtf.ValidationError(
                'You cannot have a project in the same channel twice.'
            )]

    return render_template('new_channel.html',
        project=p,
        form=form
    )


@projects.route('/<u>/<p>/channel/delete/<int:cid>', methods=['GET', 'POST'])
@user_required
@project_action
def delete_channel(u, p, cid):
    """
    Delete an existing service hook.
    """
    c = Channel.query.filter_by(
        id=cid,
        project_id=p.id
    ).first()

    if not c:
        # Project or channel doesn't exist (404 Not Found)
        return abort(404)

    if c.project.owner.id != g.user.id or c.project.id != p.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    if request.method == 'POST' and request.form.get('do') == 'd':
        c.project.channels.remove(c)
        db.session.delete(c)
        db.session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))

    return render_template('delete_channel.html',
        project=c.project,
        channel=c
    )
