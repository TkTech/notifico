from flask import (
    Blueprint,
    g,
    url_for,
    redirect
)

from notifico import user_required
from notifico.models import Group

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
