from flask import (
    Blueprint,
    g,
    url_for,
    redirect,
    request,
    render_template,
    flash
)

from notifico import user_required, group_required
from notifico.models import Group, Project, Channel, Hook

admin = Blueprint('admin', __name__, template_folder='templates')


@admin.route('/make')
@user_required
def admin_make():
    """
    Adds the current user to the 'admin' group, only if there are no
    existing admins.
    """
    if Group.query.filter_by(name='admin').count():
        # A user in the 'admin' group already exists.
        return redirect(url_for('public.landing'))

    g.user.add_group('admin')
    g.db.session.commit()
    return redirect(url_for('public.landing'))


@admin.route('/projects/', defaults={'page': 1})
@admin.route('/projects/<int:page>')
@group_required('admin')
def admin_projects(page=1):
    per_page = min(int(request.args.get('l', 25)), 100)
    sort_by = request.args.get('s', 'created')

    q = Project.query.order_by(False)
    q = q.order_by({
        'created': Project.created.desc(),
        'messages': Project.message_count.desc()
    }.get(sort_by, Project.created.desc()))

    pagination = q.paginate(page, per_page, False)

    return render_template('admin_projects.html',
        pagination=pagination,
        per_page=per_page
    )


@admin.route('/projects/delete/<int:pid>')
@group_required('admin')
def delete_project(pid):
    p = Project.query.get(pid)
    if not p:
        flash('That project does not exist.', 'error')
        return redirect(url_for('.admin_projects'))

    g.db.session.delete(p)
    g.db.session.commit()

    return redirect(url_for('.admin_projects'))


@admin.route('/orphan')
@group_required('admin')
def admin_orphans():
    """
    Murders all orphans.
    """
    # Clean up orphaned channels.
    g.db.session.query(Channel).\
        filter(~Channel.project.has()).\
        delete(synchronize_session=False)

    # Clean up orphaned hooks.
    g.db.session.query(Hook).\
        filter(~Hook.project.has()).\
        delete(synchronize_session=False)

    g.db.session.commit()

    return 'Orphans cleaned.'
