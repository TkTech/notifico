from collections import namedtuple

PermissionInfo = namedtuple('PermissionInfo', [
    'key',
    'name',
    'description'
])

#: A global index of all permissions used throughout Notifico. If you add
#: a new permission check, you should add it here as well or it will not
#: appear on the admin panel.
CORE_PERMISSIONS = (
    PermissionInfo('can_register', 'Can Register', (
        'Users with this permission can register new accounts. Typically'
        ' only used by the Anonymous user group.'
    )),
    PermissionInfo('create_project', 'Can Create Projects', (
        'Users with this permission can create new projects.'
    )),
    PermissionInfo('create_provider', 'Can Create Sources', (
        'Users with this permission can create new sources.'
    )),
    PermissionInfo('create_channel', 'Can Create Channel', (
        'Users with this permission can create new channels.'
    ))
)

PERMISSIONS = {v.key: v for v in CORE_PERMISSIONS}
