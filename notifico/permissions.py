import enum
from functools import wraps

from flask import g, redirect, url_for


class NotAllowed(Exception):
    pass


class Permission(enum.Enum):
    #: The superuser permission ignores all other permission checks.
    SUPERUSER = 'superuser'


class Action(enum.IntEnum):
    CREATE = 10
    READ = 20
    UPDATE = 30
    DELETE = 40


def has_permission(permission: Permission) -> bool:
    """
    Returns True if the current user has the permission `name`, otherwise
    returns False.
    """
    if not g.user:
        return False

    for user_permission in g.user.permissions:
        if user_permission.name == permission.value:
            return True

    return False


class HasPermissions:
    """
    Interface mixin for models that support having Permissions.
    """
    @classmethod
    def can(cls, action: Action, *, obj=None):
        if has_permission(Permission.SUPERUSER):
            return True
        return False

    @classmethod
    def only_readable(cls, q):
        """
        Modify the provided query to only return models the user should
        be allowed to see.
        """


def require_permission(permission: Permission):
    """
    A decorator which requires that there be a current user with the given
    permission, otherwise it redirects to the login page.
    """
    def _decorator(f):
        @wraps(f)
        def _wrapped(*args, **kwargs):
            if not has_permission(permission):
                return redirect(url_for('account.login'))
            return f(*args, **kwargs)
        return _wrapped
    return _decorator
