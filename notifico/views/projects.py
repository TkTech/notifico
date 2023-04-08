from functools import wraps

from flask import (
    Blueprint,
    current_app, render_template,
    g,
    redirect,
    url_for,
    abort,
    request, flash
)
import flask_wtf as wtf
from flask_babel import lazy_gettext as _
from wtforms import fields, validators

from notifico import user_required, csrf
from notifico.database import db_session
from notifico.models import User, Project, Hook, Channel, IRCNetwork
from notifico.permissions import Action
from notifico.service import incoming_services
from notifico.services.messages import MessageService

projects = Blueprint('projects', __name__, template_folder='templates')


class ProjectDetailsForm(wtf.FlaskForm):
    name = fields.StringField(
        _('Project Name'),
        validators=[
            validators.InputRequired(),
            validators.Length(1, 50),
            validators.Regexp(r'^[a-zA-Z0-9_\-\.]*$', message=_(
                'Project name must only contain a to z, 0 to 9, dashes'
                ' and underscores.'
            )),
        ],
        description=_(
            'A descriptive name for your project.'
        )
    )
    public = fields.BooleanField(
        _('Public'),
        default=True,
        description=_(
            'Should others be able to see your project? A public project will'
            ' show up in the community and in search engines.'
        )
    )
    website = fields.StringField(
        _('Project URL'),
        validators=[
            validators.Optional(),
            validators.Length(max=1024),
            validators.URL()
        ],
        description=_(
            'Project URLs are not public. They may be used to confirm'
            ' ownership of a project in the case of lost credentials.'
        )
    )


class HookDetailsForm(wtf.FlaskForm):
    service_id = fields.SelectField('Service', validators=[
        validators.InputRequired()
    ], coerce=int)


class ChannelEditForm(wtf.FlaskForm):
    channel = fields.StringField(
        _('Channel'),
        validators=[
            validators.InputRequired(),
            validators.Length(min=1, max=80)
        ],
        description=_(
            'The channel to join, including any prefixes, such as'
            ' #commits or ##my-project.'
        )
    )
    password = fields.PasswordField(
        _('Password'),
        validators=[
            validators.Optional(),
            validators.Length(min=1, max=80)
        ],
        description=_(
            'The password needed to join the channel, if one is required. Most'
            ' IRC channels do not require a password.'
        )
    )
    public = fields.BooleanField(
        _('Public'),
        default=True,
        description=_(
            'Allow others to see that this channel exists.'
        )
    )

    def validate_public(self, field: fields.StringField):
        channel: Channel | None = getattr(self.meta, 'channel', None)
        if channel and channel.logged and field.data is False:
            raise validators.ValidationError(
                _('Channel cannot be made private while logging is enabled.')
            )

    def validate_password(self, field: fields.StringField):
        channel: Channel = self.meta.channel
        if channel.logged and field.data:
            raise validators.ValidationError(_(
                'Channel cannot have a password set while logging is enabled.'
            ))


class ChannelCreateForm(ChannelEditForm):
    network = fields.SelectField(
        _('Network')
    )


class ChannelLoggingForm(wtf.FlaskForm):
    enabled = fields.BooleanField(
        _('Enable Logging'),
        default=False,
        description=_(
            'Enable logging for this channel.'
        )
    )

    def validate_enabled(self, field: fields.StringField):
        channel: Channel = self.meta.channel
        if not channel.public:
            raise validators.ValidationError(_('Channel must be public.'))

        if channel.password:
            raise validators.ValidationError(
                _('Channel must not have a password.')
            )


class ChannelDeleteForm(wtf.FlaskForm):
    confirm_channel = fields.StringField(
        _('Channel Name'),
        validators=[
            validators.InputRequired()
        ],
        description=_(
            'Type the name of the channel to confirm deletion.'
        )
    )

    def validate_confirm_channel(self, field: fields.StringField):
        if self.meta.channel.channel != field.data:
            raise validators.ValidationError(_('Channel name does not match.'))


class ProjectDeleteForm(wtf.FlaskForm):
    confirm_project = fields.StringField(
        _('Project Name'),
        validators=[
            validators.InputRequired()
        ]
    )

    def validate_confirm_project(self, field: fields.StringField):
        if self.meta.project.name != field.data:
            raise validators.ValidationError(_('Project name does not match.'))


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
def dashboard(u: User):
    """
    Display an overview of all the user's projects with summary
    statistics.
    """
    u = User.by_username(u)
    if not u:
        return abort(404)

    if not User.can(Action.READ, obj=u):
        return abort(403)

    user_projects = (
        u.projects
        .order_by(False)
        .order_by(Project.created.desc())
    )

    return render_template(
        'projects/dashboard.html',
        user=u,
        projects=user_projects,
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
    if not Project.can(Action.CREATE):
        return abort(403)

    form = ProjectDetailsForm()
    if form.validate_on_submit():
        p = Project.by_name_and_owner(form.name.data, g.user)
        if p:
            form.name.errors = [
                validators.ValidationError('Project name must be unique.')
            ]
        else:
            p = Project.new(
                form.name.data,
                public=form.public.data,
                website=form.website.data
            )
            g.user.projects.append(p)
            db_session.add(p)
            db_session.commit()

            return redirect(url_for('.details', u=g.user.username, p=p.name))

    return render_template(
        'projects/new_project.html',
        form=form,
        action='new'
    )


@projects.route('/<u>/<p>/edit', methods=['GET', 'POST'])
@user_required
@project_action
def edit_project(u: User, p: Project):
    """
    Edit an existing project.
    """
    if not Project.can(Action.UPDATE, obj=p):
        return abort(403)

    delete_form = ProjectDeleteForm(prefix='delete', meta={'project': p})
    edit_form = ProjectDetailsForm(prefix='edit', obj=p)

    match request.form.get('action'):
        case 'edit':
            if edit_form.validate_on_submit():
                old_p = Project.by_name_and_owner(edit_form.name.data, g.user)
                if old_p and old_p.id != p.id:
                    edit_form.name.errors = [
                        validators.ValidationError(
                            _('Project name must be unique.')
                        )
                    ]
                else:
                    p.name = edit_form.name.data
                    p.website = edit_form.website.data
                    p.public = edit_form.public.data
                    db_session.commit()
                    flash(
                        _('Changes to your project have been saved.'),
                        category='success'
                    )
                    return redirect(p.url(p.Page.DETAILS))
        case 'delete':
            if delete_form.validate_on_submit():
                db_session.delete(p)
                db_session.commit()

                flash(
                    _('Your project has been deleted.'),
                    category='success'
                )

                return redirect(u.url(u.Page.DASHBOARD))

    return render_template(
        'projects/edit_project.html',
        project=p,
        edit_form=edit_form,
        delete_form=delete_form
    )


@projects.route('/<u>/<p>')
@project_action
def details(u, p: Project):
    """
    Show the details for an existing project.
    """
    if not Project.can(Action.READ, obj=p):
        return abort(403)

    return render_template(
        'projects/project_details.html',
        project=p,
        user=u,
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
def new_hook(u, p: Project, sid):
    if not Project.can(Action.UPDATE, obj=p):
        return abort(403)

    hook = incoming_services()[sid]
    form = hook.form()
    if form:
        form = form()

    if form and hook.validate(form, request):
        h = Hook(service_id=sid, config=hook.pack_form(form))
        p.hooks.append(h)
        db_session.add(h)
        db_session.commit()
        return render_template(
            'projects/hook_ready.html',
            project=p,
            hook=h
        )
    elif form is None and request.method == 'POST':
        h = Hook(service_id=sid)
        p.hooks.append(h)
        db_session.add(h)
        db_session.commit()
        return render_template(
            'projects/hook_ready.html',
            project=p,
            hook=h
        )

    return render_template(
        'projects/new_hook.html',
        project=p,
        services=incoming_services(),
        service=hook,
        form=form,
        action='new'
    )


@projects.route('/<u>/<p>/hook/edit/<int:hid>', methods=['GET', 'POST'])
@user_required
@project_action
def edit_hook(u, p: Project, hid):
    if not Project.can(Action.UPDATE, obj=p):
        return abort(403)

    h = Hook.query.get(hid)
    if h is None:
        # You can't edit a hook that doesn't exist!
        return abort(404)

    hook_service = h.hook()
    form = hook_service.form()
    if form:
        form = form()

    if form and hook_service.validate(form, request):
        h.config = hook_service.pack_form(form)
        db_session.add(h)
        db_session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form is None and request.method == 'POST':
        db_session.add(h)
        db_session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))
    elif form:
        hook_service.load_form(form, h.config)

    return render_template(
        'projects/new_hook.html',
        project=p,
        services=incoming_services(),
        service=hook_service,
        form=form,
        action='edit',
        hook=h
    )


@projects.route('/h/<int:pid>/<key>', methods=['GET', 'POST'])
@csrf.exempt
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

    hook = incoming_services()[h.service_id]
    if hook is None:
        # TODO: This should be logged somewhere.
        return ''

    hook._request(h.project.owner, request, h)

    db_session.commit()
    return ''


@projects.route('/<u>/<p>/hook/delete/<int:hid>', methods=['GET', 'POST'])
@user_required
@project_action
def delete_hook(u, p: Project, hid):
    """
    Delete an existing service hook.
    """
    if not Project.can(Action.UPDATE, obj=p):
        return abort(403)

    h = Hook.query.get(hid)
    if not h:
        # Project doesn't exist (404 Not Found)
        return abort(404)

    if request.method == 'POST' and request.form.get('do') == 'd':
        p.hooks.remove(h)
        db_session.delete(h)
        db_session.commit()
        return redirect(url_for('.details', p=p.name, u=u.username))

    return render_template(
        'projects/delete_hook.html',
        project=p,
        hook=h
    )


@projects.route('/<u>/<p>/channel/new', methods=['GET', 'POST'])
@user_required
@project_action
def new_channel(u, p: Project):
    if not Project.can(Action.UPDATE, obj=p):
        return abort(403)

    # Get the networks the current user has used for any of their projects,
    # and all public networks.
    networks = IRCNetwork.only_readable(
        db_session.query(IRCNetwork)
    ).order_by(
        IRCNetwork.public.asc()
    ).all()

    # Get the user's most recently used channels from other projects as
    # shortcuts.
    common_channels = Channel.only_readable(
        db_session.query(Channel)
    ).join(
        Channel.project
    ).filter(
        Project.owner_id == g.user.id,
        Channel.project_id != p.id
    ).distinct(
        Channel.network_id
    ).order_by(
        Channel.network_id,
        Channel.created.desc()
    ).limit(
        3
    ).all()

    form = ChannelCreateForm()
    form.network.choices = []

    for network in networks:
        if network.public is not None and network.public > 0:
            # We simplify the display of public networks - it really doesn't
            # matter what port it's on or if it's using SSL, and these things
            # may even change as networks are merged.
            form.network.choices.append(
                (network.id, f'{network.host}')
            )
        elif network.ssl:
            form.network.choices.append((
                network.id,
                f'★ {network.host}:{network.port} (Using SSL)'
            ))
        else:
            form.network.choices.append((
                network.id,
                f'★ {network.host}:{network.port}'
            ))

    if request.method == 'POST':
        if request.form.get('action') == 'quick-add':
            channel = db_session.query(
                Channel
            ).filter(
                Channel.id == request.form['channel-id']
            ).first()

            if not channel:
                abort(404)
            elif not channel.can(Action.READ, obj=channel):
                abort(403)

            db_session.add(
                Channel(
                    channel=channel.channel,
                    network=channel.network,
                    public=channel.public,
                    password=channel.password,
                    project=p
                )
            )
            db_session.commit()
            flash(
                _('The channel has been added to your project.'),
                category='success'
            )
            return redirect(p.url(p.Page.DETAILS))
        elif form.validate_on_submit():
            network = IRCNetwork.query.get(form.network.data)
            if not IRCNetwork.can(Action.READ, obj=network):
                abort(403)

            channel = form.channel.data

            # Make sure this isn't a duplicate channel before we create it.
            c = Channel.query.filter_by(
                channel=channel,
                network=network,
                project_id=p.id
            ).first()
            if not c:
                c = Channel(
                    channel=channel,
                    network=network,
                    password=form.password.data,
                    public=form.public.data
                )
                p.channels.append(c)
                db_session.add(c)
                db_session.commit()

                flash(
                    _('The channel has been added to your project.'),
                    category='success'
                )
                return redirect(p.url(p.Page.DETAILS))
            else:
                form.channel.errors = [
                    validators.ValidationError(
                        'You cannot have a project in the same channel twice.'
                    )
                ]

    return render_template(
        'projects/new_channel.html',
        project=p,
        networks=networks,
        form=form,
        common_channels=common_channels
    )


@projects.route('/<u>/<p>/channel/<int:cid>/edit', methods=['GET', 'POST'])
@user_required
@project_action
def edit_channel(u, p: Project, cid):
    """
    Edit an existing channel.
    """
    if not Project.can(Action.UPDATE, obj=p):
        return abort(403)

    c: Channel = Channel.query.filter_by(
        id=cid,
        project_id=p.id
    ).first()

    if not c:
        return abort(404)

    edit_form = ChannelEditForm(prefix='edit', obj=c, meta={'channel': c})
    logging_form = ChannelLoggingForm(
        prefix='logging',
        data={
            'enabled': c.logged
        },
        meta={
            'channel': c
        }
    )
    delete_form = ChannelDeleteForm(prefix='delete', meta={'channel': c})

    ms = MessageService(redis=current_app.redis)  # noqa

    match request.form.get('action'):
        case 'edit':
            if edit_form.validate_on_submit():
                edit_form.populate_obj(c)
                db_session.commit()
                flash(_('The channel has been updated.'), category='success')
                return redirect(url_for('.details', p=p.name, u=u.username))
        case 'delete':
            if delete_form.validate_on_submit():
                c.project.channels.remove(c)
                db_session.delete(c)
                db_session.commit()
                flash(_('The channel has been deleted.'), category='success')
                return redirect(url_for('.details', p=p.name, u=u.username))
        case 'logging':
            if logging_form.validate_on_submit():
                c.logged = logging_form.enabled.data
                db_session.add(c)
                db_session.commit()
                if c.logged:
                    flash(
                        _('Logging has been enabled for this channel.'),
                        category='success'
                    )
                    ms.start_logging(c)
                else:
                    flash(
                        _('Logging has been disabled for this channel.'),
                        category='success'
                    )
                    ms.stop_logging(c)

                return redirect(url_for('.details', p=p.name, u=u.username))

    return render_template(
        'projects/edit_channel.html',
        project=c.project,
        channel=c,
        edit_form=edit_form,
        logging_form=logging_form,
        delete_form=delete_form
    )
