from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash
)
from flask_babel import lazy_gettext as _
from flask_login import login_user, logout_user, login_required, current_user

from notifico.extensions import db
from notifico.models.user import User
from notifico.models.group import Group, CoreGroups
from notifico.authorization import require_permission
from notifico.forms.users import (
    UserLoginForm,
    UserRegisterForm
)

users = Blueprint('users', __name__)
# Usernames that cannot be registered because they clash with existing or
# planned internal routes.
_reserved = (
    'new',
    'api',
    'settings',
    'login',
    'logout',
    'stats',
)


@users.route('/login', methods=['GET', 'POST'])
def login():
    """
    Standard login form.
    """
    if current_user.is_active:
        return redirect(url_for('public.landing'))

    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.by_username(form.username.data)
        login_user(user)

        return redirect(user.dashboard_url)

    return render_template('users/login.html', form=form)


@users.route('/logout')
@login_required
def logout():
    """
    Logout the current user.
    """
    logout_user()
    return redirect(url_for('.login'))


@users.route('/register', methods=['GET', 'POST'])
@require_permission('can_register', login_required=False)
def register():
    """
    If new user registrations are enabled, provides a registration form
    and validation.
    """
    if current_user.is_active:
        return redirect(url_for('public.landing'))

    form = UserRegisterForm()
    if form.validate_on_submit():
        # Checks out, go ahead and create our new user.
        u = User.new(form.username.data, form.email.data, form.password.data)

        # Add to the Registered core user group.
        u.groups.append(Group.query.get(CoreGroups.REGISTERED.value))

        db.session.add(u)
        db.session.commit()
        # ... and send them back to the login screen.
        flash(
            _('Your account has been created, please login.'),
            category='success'
        )
        return redirect(url_for('.login'))

    return render_template('users/register.html', form=form)
