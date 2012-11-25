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
from notifico.services import registered_services, service_from_id

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


@projects.route('/hook/new/<int:pid>', methods=['GET', 'POST'])
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
        h = Hook.new(form.service_id.data)
        p.hooks.append(h)
        g.db.session.add(h)
        g.db.session.commit()
        flash('Your hook has been created.', 'success')
        return redirect(url_for('.details', pid=pid))

    return render_template('new_hook.html',
        project=p,
        form=form
    )


@projects.route('/h/<int:pid>/<key>', methods=['GET', 'POST'])
def hook_recieve(pid, key):
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

    service = service_from_id(h.service_id)
    if service is None:
        # TODO: This should be logged somewhere.
        return ''

    service._request(h.project.owner, request, h)

    g.db.session.commit()
    return ''


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


@projects.route('/channel/new/<int:pid>', methods=['GET', 'POST'])
@user_required
def new_channel(pid):
    p = Project.query.get(pid)
    if not p:
        # Project doesn't exist (404 Not Found)
        return abort(404)

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
            project_id=pid
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
            return redirect(url_for('.details', pid=pid))
        else:
            form.channel.errors = [wtf.ValidationError(
                'You cannot have a project in the same channel twice.'
            )]

    return render_template('new_channel.html',
        project=p,
        form=form
    )


@projects.route('/channel/delete/<int:pid>/<int:cid>', methods=['GET', 'POST'])
@user_required
def delete_channel(pid, cid):
    """
    Delete an existing service hook.
    """
    c = Channel.query.filter_by(id=cid, project_id=pid).first()
    if not c:
        # Project or channel doesn't exist (404 Not Found)
        return abort(404)

    if c.project.owner.id != g.user.id or c.project.id != pid:
        # Project isn't public and the viewer isn't the project owner.
        # (403 Forbidden)
        return abort(403)

    if request.method == 'POST' and request.form.get('do') == 'd':
        c.project.channels.remove(c)
        g.db.session.delete(c)
        g.db.session.commit()
        flash('The channel has been removed.', 'success')
        return redirect(url_for('.details', pid=pid))

    return render_template('delete_channel.html',
        project=c.project,
        channel=c
    )
