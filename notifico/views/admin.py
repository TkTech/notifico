from flask import (
    Blueprint,
    render_template,
    url_for,
    request,
    abort,
    redirect,
    flash
)
from flask_login import login_required
from flask_babel import lazy_gettext as _

from notifico.extensions import db
from notifico.models import Group, Permission
from notifico.forms.admin import make_permission_form, GroupDetailsForm


admin = Blueprint('admin', __name__)


@admin.route('/')
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
def groups_delete(group_id):
    crumbs = (
        (_('Admin'), url_for('.dashboard')),
        (_('Groups'), url_for('.groups')),
        (_('Delete Group'), None)
    )

    group = Group.query.get(group_id)
    if group is None:
        abort(404)

    if request.method == 'POST' and 'delete-group' in request.form:
        db.session.delete(group)
        db.session.commit()

        flash(_('The group has been deleted.'), category='success')
        return redirect(url_for('.groups'))

    return render_template(
        'admin/groups/delete.html',
        admin_title=_('Delete Group'),
        breadcrumbs=crumbs,
        group=group
    )
