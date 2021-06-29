from functools import wraps

from flask import flash, url_for, redirect
from flask_login import current_user
from flask_babel import lazy_gettext as _

from notifico.extensions import db
from notifico.models.user import User
from notifico.models.group import Group, Permission, CoreGroups


def has_admin(f):
    """
    A decorator to protect views. Requires a logged in admin account to
    view.
    """
    @wraps(f)
    def _wrapped(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_admin:
            return f(*args, **kwargs)

        flash(_(
            'You do not have the required permissions for that'
            ' action.'
        ), category='danger')
        return redirect(url_for('users.login'))

    return _wrapped


def has_permission(key, *, login_required=True):
    """
    Check to see if the current user has the permission given by `key`.

    If `login_required` is True (the default), users must be logged in or
    this always fails. If `False`, logged out users will be checked against
    the Anonymous user group.
    """
    # Admins skip all permission checks.
    if current_user.is_authenticated and current_user.is_admin:
        return True

    if current_user.is_authenticated:
        return db.session.query(
            Permission.query.join(
                Permission, Group.permissions
            ).join(
                User, User.groups
            ).filter(
                Permission.key == key
            ).exists()
        ).scalar()
    elif not login_required:
        # If logins are not required, check the defaults inherited from the
        # Anonymous user group.
        return db.session.query(
            Permission.query.join(
                Permission, Group.permissions
            ).filter(
                Group.id == CoreGroups.ANONYMOUS.value,
                Permission.key == key
            ).exists()
        ).scalar()

    return False


def require_permission(key, *, login_required=True):
    """
    A decorator to protect views. The permission given by `key` is required
    to continue.

    If `login_required` is `True` (the default), then a user must be logged
    in before any permission check. You may want to disable this when looking
    for permissions on an Anonymous user.
    """
    def _wrap(f):
        @wraps(f)
        def _wrapped(*args, **kwargs):
            if has_permission(key, login_required=login_required):
                return f(*args, **kwargs)

            flash(_(
                'You do not have the required permissions for that'
                ' action.'
            ), category='danger')

            return redirect(url_for('users.login'))
        return _wrapped
    return _wrap
