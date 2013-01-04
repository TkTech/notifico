from functools import wraps

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

from notifico import user_required
from notifico.models import User, Project, Hook, Channel
from notifico.services.hooks import HookService

projects = Blueprint('projects', __name__, template_folder='templates')


class ProjectDetailsForm(wtf.Form):
    name = wtf.TextField('Project Name', validators=[
        wtf.Required(),
        wtf.Length(2, 50),
        wtf.Regexp('^[a-zA-Z0-9_]*$', message=(
            'Project name must only contain a to z, 0 to 9, and underscores.'
        ))
    ])
    public = wtf.BooleanField('Public', validators=[
    ], default=True)
    website = wtf.TextField('Project URL', validators=[
        wtf.Optional(),
        wtf.Length(max=1024),
        wtf.validators.URL()
    ])


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


class ChannelDetailsForm(wtf.Form):
    channel = wtf.TextField('Channel', validators=[
        wtf.Required(),
        wtf.Length(min=1, max=80)
    ])
    host = wtf.TextField('Host', validators=[
        wtf.Required(),
        wtf.Length(min=1, max=255)
    ], default='irc.freenode.net')
    port = wtf.IntegerField('Port', validators=[
        wtf.NumberRange(1024, 66552)
    ], default=6667)
    ssl = wtf.BooleanField('Use SSL', default=False)
    public = wtf.BooleanField('Public', default=True, description=(
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
def overview(u):
    """
    Display an overview of all the user's projects with summary
    statistics.
    """
    u = User.by_username(u)
    if not u:
        # No such user exists.
        return abort(404)

    is_owner = (g.user and g.user.id == u.id)

    return render_template('overview.html',
        user=u,
        is_owner=is_owner
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
            g.db.session.add(p)

            if p.public:
                # New public projects get added to #commits by default.
                c = Channel.new(
                    '#commits',
                    'irc.freenode.net',
                    6667,
                    ssl=False,
                    public=True
                )
                p.channels.append(c)

            g.db.session.commit()

            flash('Your project has been created.', 'success')
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
            g.db.session.commit()
            flash('Your changes have been saved.', 'success')
            return redirect(url_for('.overview', u=u.username))

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

    form = PasswordConfirmForm()
    if form.validate_on_submit():
        g.db.session.delete(p)
        g.db.session.commit()
        flash('Your project has been deleted.', 'success')
        return redirect(url_for('.overview', u=u.username))

    return render_template('delete_project.html',
        project=p,
        form=form
    )


@projects.route('/<u>/<p>')
@project_action
def details(u, p):
    """
    Show an existing project's details.
    """
    if not p.public and not g.user:
        # Not public and no logged in user. (Forbidden)
        return abort(403)
    elif not p.public and p.owner.id != g.user.id:
        # Not public and not owner. (Forbidden)
        return abort(403)

    is_owner = (g.user and g.user.id == p.owner_id)

    status_cache = {}

    def channel_status(channel):
        if channel.id not in status_cache:
            last_event = channel.last_event()
            if last_event is None:
                status_cache[channel.id] = '-'
            else:
                status_cache[channel.id] = last_event.status
        return status_cache[channel.id]

    return render_template('project_details.html',
        project=p,
        is_owner=is_owner,
        user=u,
        channel_status=channel_status
    )


@projects.route('/<u>/<p>/hook/new',
    defaults={'sid': 10}, methods=['GET', 'POST'])
@projects.route('/<u>/<p>/hook/new/<int:sid>', methods=['GET', 'POST'])
@user_required
@project_action
def new_hook(u, p, sid):
    if p.owner.id != g.user.id:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    hook = HookService.services.get(sid)
    form = hook.form()
    if form:
        form = form()

    if form and hook.validate(form, request):
        h = Hook.new(sid, config=hook.pack_form(form))
        p.hooks.append(h)
        g.db.session.add(h)
        g.db.session.commit()
        flash('Your hook has been created.', 'success')
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form is None and request.method == 'POST':
        h = Hook.new(sid)
        p.hooks.append(h)
        g.db.session.add(h)
        g.db.session.commit()
        flash('Your hook has been created.', 'success')
        return redirect(url_for('.details', p=p.name, u=u.username))

    return render_template('new_hook.html',
        project=p,
        services=HookService.services,
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
        g.db.session.add(h)
        g.db.session.commit()
        flash('Your hook has been saved.', 'success')
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form is None and request.method == 'POST':
        g.db.session.add(h)
        g.db.session.commit()
        flash('Your hook has been saved.', 'success')
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form:
        hook_service.load_form(form, h.config)

    return render_template('edit_hook.html',
        project=p,
        services=HookService.services,
        service=hook_service,
        form=form
    )


@projects.route('/h/<int:pid>/<key>', methods=['GET', 'POST'])
def hook_receive(pid, key):
    h = Hook.query.filter_by(key=key, project_id=pid).first()
    if not h:
        return abort(404)

    # Increment the hooks message_count....
    Hook.query.filter_by(id=h.id).update({
        Hook.message_count: Hook.message_count + 1
    })
    # ... and the project-wide message_count.
    Project.query.filter_by(id=h.project.id).update({
        Project.message_count: Project.message_count + 1
    })

    hook = HookService.services.get(h.service_id)
    if hook is None:
        # TODO: This should be logged somewhere.
        return ''

    hook._request(h.project.owner, request, h)

    g.db.session.commit()
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
        g.db.session.delete(h)
        g.db.session.commit()
        flash('The hook has been deleted.', 'success')
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
            g.db.session.add(c)
            g.db.session.commit()
            flash('Your channel has been created.', 'success')
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
        g.db.session.delete(c)
        g.db.session.commit()
        flash('The channel has been removed.', 'success')
        return redirect(url_for('.details', p=p.name, u=u.username))

    return render_template('delete_channel.html',
        project=c.project,
        channel=c
    )
