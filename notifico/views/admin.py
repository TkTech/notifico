import json

from flask import (
    Blueprint,
    render_template,
    url_for,
    request,
    abort,
    redirect,
    flash,
    current_app
)
from flask_babel import lazy_gettext as _

from notifico.extensions import db
from notifico.models import (
    Group,
    Permission,
    Log,
    LogContext,
    Project,
    User,
    Channel,
    Plugin as PluginModel
)
from notifico.models.log import LogContextType
from notifico.models.group import CoreGroups
from notifico.authorization import has_admin
from notifico.forms.admin import (
    make_permission_form,
    GroupDetailsForm,
    UserFilterForm,
    GroupSelectForm
)
from notifico.views.utils import confirmation_view, ConfirmPrompt
from notifico.plugins.core import all_available_plugins


admin = Blueprint('admin', __name__)


prompt_users_delete_group = ConfirmPrompt(
    cancel_url=lambda user_id, group_id: url_for(
        '.users_edit',
        user_id=user_id
    ),
    message=_('Are you sure you want to remove this group?'),
    yes_text=_('Remove Group'),
    template='admin/confirm.html'
)

prompt_delete_group = ConfirmPrompt(
    cancel_url=lambda group_id: url_for('.groups'),
    message=_(
        'All users will be removed from the group and the group deleted.'
        ' Are you sure?'
    ),
    yes_text=_('Delete Group'),
    template='admin/confirm.html'
)

prompt_delete_user = ConfirmPrompt(
    cancel_url=lambda user_id: url_for('.users'),
    message=_(
        'This user will be permanently deleted. This cannot be undone.'
        ' Are you sure?'
    ),
    yes_text=_('Delete User'),
    template='admin/confirm.html'
)

prompt_delete_plugin_group = ConfirmPrompt(
    cancel_url=lambda plugin_id, group_id: url_for(
        '.plugins_edit',
        plugin_id=plugin_id
    ),
    message=_(
        'Are you sure you want to remove this group?'
    ),
    yes_text=_('Remove Group'),
    template='admin/confirm.html'
)


@admin.route('/')
@has_admin
def dashboard():
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Dashboard'), None)
    )

    return render_template(
        'admin/dashboard.html',
        admin_title=_('Dashboard'),
        breadcrumbs=crumbs
    )


@admin.route('/groups')
@has_admin
def groups():
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Groups'), None)
    )

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    # User groups can be deleted.
    user_groups = Group.query.filter(
        Group.deletable.is_(True)
    ).paginate(
        page=page,
        per_page=15
    )

    # Core groups, like anonymous and registered, cannot be removed nor
    # renamed.
    core_groups = Group.query.filter(
        Group.deletable.is_(False)
    )

    return render_template(
        'admin/groups/list.html',
        admin_title=_('Groups'),
        breadcrumbs=crumbs,
        core_groups=core_groups,
        user_groups=user_groups,
        page=page
    )


@admin.route('/groups/new', methods=['GET', 'POST'])
@has_admin
def groups_new():
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Groups'), url_for('.groups')),
        (_('New Group'), None)
    )

    form = GroupDetailsForm()
    if form.validate_on_submit():
        group = Group(
            name=form.name.data,
            description=form.description.data
        )

        db.session.add(group)
        db.session.commit()

        flash(_('Your group has been created.'), category='success')
        return redirect(group.edit_url)

    return render_template(
        'admin/groups/new.html',
        admin_title=_('Group Settings'),
        breadcrumbs=crumbs,
        form=form,
    )


@admin.route('/groups/<int:group_id>', methods=['GET', 'POST'])
@has_admin
def groups_edit(group_id):
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Groups'), url_for('.groups')),
        (_('Settings'), None)
    )

    group = Group.query.get(group_id)
    if group is None:
        abort(404)

    permissions = group.permission_matrix()
    permissions_form = make_permission_form(permissions)()

    details_form = GroupDetailsForm(data={
        'name': group.name,
        'description': group.description
    })

    # User is updating the permissions on the group.
    if 'save-permissions' in request.form:
        if permissions_form.validate_on_submit():
            # The performance of this is awful, but editing group permissions
            # should be incredibly infrequent. We should pre-create every
            # permission on migration, and just assume they exist.
            group.permissions = [
                Permission.get(field.id)
                for field in permissions_form
                if field.data is True
            ]

            db.session.add(group)
            db.session.commit()

            flash(_('Your changes have been saved.'), category='success')
            return redirect(group.edit_url)

    # User is updating the details on the group.
    if 'save-details' in request.form:
        # This should *never* happen unless someone is poking around.
        if group.deletable is False:
            abort(403)

        if details_form.validate_on_submit():
            group.name = details_form.name.data
            group.description = details_form.description.data

            db.session.add(group)
            db.session.commit()

            flash(_('Your changes have been saved.'), category='success')
            return redirect(group.edit_url)

    return render_template(
        'admin/groups/edit.html',
        admin_title=_('Group Settings'),
        breadcrumbs=crumbs,
        group=group,
        permissions_form=permissions_form,
        permissions={v.key: v for v in permissions.keys()},
        details_form=details_form
    )


@admin.route('/groups/<int:group_id>/delete', methods=['GET', 'POST'])
@has_admin
@confirmation_view(prompt_delete_group)
def groups_delete(group_id):
    group = Group.query.get(group_id)
    if group is None:
        abort(404)

    if not group.deletable:
        flash(
            _('This is a core group and cannot be removed.'),
            category='danger'
        )
        return redirect(url_for('.groups'))

    db.session.delete(group)
    db.session.commit()

    flash(_('The group has been deleted.'), category='success')
    return redirect(url_for('.groups'))


@admin.route('/users', endpoint='users')
@has_admin
def users_list():
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Users'), None),
    )

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    form = UserFilterForm(request.args, meta={'csrf': False})
    # The list of groups is unknown when the form is created, so we need
    # to populate it.
    form.group.choices = [
        (group.id, group.name)
        for group in Group.query.with_entities(Group.id, Group.name)
    ]
    # If no group has been explicitly provided, default to the registered
    # user group.
    if 'group' not in request.args:
        form.group.data = next(
            gid for gid, _ in form.group.choices
            if gid == CoreGroups.REGISTERED.value
        )

    if form.validate():
        pass

    users = db.session.query(
        User
    ).join(
        User.groups
    ).filter(
        Group.id == form.group.data
    )

    users = users.order_by(User.joined.desc()).paginate(
        page=page,
        per_page=25
    )

    return render_template(
        'admin/users/list.html',
        admin_title=_('Users'),
        breadcrumbs=crumbs,
        users=users,
        form=form
    )


@admin.route('/users/<int:user_id>', methods=['GET', 'POST'])
@has_admin
def users_edit(user_id):
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Users'), url_for('.users')),
        (_('Edit User'), None)
    )

    user = User.query.get(user_id)
    if user is None:
        abort(404)

    logs = db.session.query(
        Log
    ).join(
        LogContext
    ).filter(
        LogContext.context_type == LogContextType.USER,
        LogContext.context_id == user_id
    ).order_by(
        Log.created.desc()
    )

    group_form = GroupSelectForm()
    group_form.group.choices = [
        (group.id, group.name)
        for group in Group.query.filter(
            Group.deletable.is_(True)
        ).with_entities(Group.id, Group.name)
    ]

    if 'add-group' in request.form:
        if group_form.validate_on_submit():
            group = Group.query.get(group_form.group.data)
            if group is None or not group.deletable:
                # We should never get here unless someone is poking around.
                flash(_('Not a valid group.'), category='warning')
            elif group in user.groups:
                flash(
                    _('User is already a member of that group.'),
                    category='warning'
                )
            else:
                user.groups.append(group)
                db.session.add(user)
                db.session.commit()
                flash(_('User added to group.'), category='success')

            return redirect(user.admin_edit_url)

    return render_template(
        'admin/users/edit.html',
        admin_title=_('Edit User'),
        breadcrumbs=crumbs,
        user=user,
        group_form=group_form,
        logs=logs
    )


@admin.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@has_admin
@confirmation_view(prompt_delete_user)
def users_delete(user_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404)

    if user.is_admin:
        flash(_('Admin users cannot be deleted.'), category='danger')
        return redirect(url_for('.users'))

    db.session.delete(user)
    db.session.commit()

    flash(_('The user has been deleted.'), category='success')
    return redirect(url_for('.users'))


@admin.route(
    '/users/<int:user_id>/groups/<int:group_id>/delete',
    methods=['GET', 'POST']
)
@has_admin
@confirmation_view(prompt_users_delete_group)
def users_delete_group(user_id, group_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404)

    group = Group.query.get(group_id)
    if group is None or not group.deletable:
        abort(404)

    user.groups.remove(group)
    db.session.add(user)
    db.session.commit()

    flash(_('The group has been removed.'), category='success')
    return redirect(url_for('.users_edit', user_id=user.id))


@admin.route('/plugins/')
@has_admin
def plugins():
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Plugins'), None)
    )

    plugins = {
        'available': all_available_plugins(),
        'installed': {p.plugin_id: p for p in PluginModel.query.all()},
        'restart': set()
    }

    for plugin in plugins['installed'].values():
        plugins['available'].pop(plugin.plugin_id)
        if plugin.plugin_id not in current_app.noti.plugins:
            # Plugin wasn't enabled when the server started.
            plugins['restart'].add(plugin.plugin_id)

    return render_template(
        'admin/plugins/list.html',
        admin_title=_('Plugins'),
        breadcrumbs=crumbs,
        plugins=plugins
    )


@admin.route('/plugins/<int:plugin_id>', methods=['GET', 'POST'])
@has_admin
def plugins_edit(plugin_id):
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Plugins'), url_for('.plugins')),
        (_('Edit Plugin'), None)
    )

    plugin = PluginModel.query.get(plugin_id)
    if plugin is None:
        abort(404)

    logs = db.session.query(
        Log
    ).join(
        LogContext
    ).filter(
        LogContext.context_type == LogContextType.PLUGIN,
        LogContext.context_id == plugin_id
    ).order_by(
        Log.created.desc()
    )

    group_form = GroupSelectForm()
    group_form.group.choices = [
        (group.id, group.name)
        for group in Group.query.with_entities(Group.id, Group.name)
    ]

    if 'add-group' in request.form:
        if group_form.validate_on_submit():
            group = Group.query.get(group_form.group.data)
            if group is None:
                flash(_('Not a valid group.'), category='warning')
            elif group in plugin.groups:
                flash(
                    _('Group already allowed on Source.'),
                    category='warning'
                )
            else:
                plugin.groups.append(group)
                db.session.add(plugin)
                db.session.commit()
                flash(_('Plugin enabled for group.'), category='success')

            return redirect(plugin.admin_edit_url)

    return render_template(
        'admin/plugins/edit.html',
        admin_title=_('Edit Plugins'),
        breadcrumbs=crumbs,
        plugin=plugin,
        impl=plugin.impl,
        logs=logs,
        group_form=group_form
    )


@admin.route(
    '/plugin/<int:plugin_id>/groups/<int:group_id>/delete',
    methods=['GET', 'POST']
)
@has_admin
@confirmation_view(prompt_delete_plugin_group)
def plugins_delete_group(plugin_id, group_id):
    plugin = PluginModel.query.get(plugin_id)
    if plugin is None:
        abort(404)

    group = Group.query.get(group_id)
    if group is None:
        abort(404)

    plugin.groups.remove(group)
    db.session.add(plugin)
    db.session.commit()

    flash(_('The group has been removed.'), category='success')
    return redirect(plugin.admin_edit_url)


@admin.route('/logs/')
@has_admin
def logs():
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Logs'), None),
    )

    logs = db.session.query(Log).order_by(
        Log.created.desc()
    )

    return render_template(
        'admin/logs/list.html',
        admin_title=_('Logs'),
        breadcrumbs=crumbs,
        logs=logs
    )


def _get_related(related: LogContext):
    if related.context_type == LogContextType.USER:
        return db.session.query(User).get(related.context_id)
    elif related.context_type == LogContextType.CHANNEL_INST:
        return db.session.query(Channel).get(related.context_id)
    elif related.context_type == LogContextType.PLUGIN:
        return db.session.query(PluginModel).get(related.context_id)
    elif related.context_type == LogContextType.PROJECT:
        return db.session.query(Project).get(related.context_id)


@admin.route('/logs/<int:log_id>')
@has_admin
def logs_get(log_id):
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Logs'), url_for('.logs')),
        (_('Details'), None)
    )

    log = db.session.query(Log).get(log_id)
    if log is None:
        abort(404)

    return render_template(
        'admin/logs/get.html',
        admin_title=_('Log Details'),
        breadcrumbs=crumbs,
        log=log,
        pretty_payload=json.dumps(log.payload, sort_keys=True, indent=2),
        get_related=_get_related
    )
