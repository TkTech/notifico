# -*- coding: utf8 -*-
__all__ = ('hook_by_id',)


from notifico.services.hooks.github import *
from notifico.services.hooks.plain import *
from notifico.services.hooks.bitbucket import *

# TODO: This really needs to be re-evaluated. At the moment, this must
#       be updated on each addition. Maybe __subclasses__() is mature enough
#       to use in a portable fashion.
_default_hooks = {
    GithubHook.SERVICE_ID: GithubHook,
    PlainTextHook.SERVICE_ID: PlainTextHook,
    BitbucketHook.SERVICE_ID: BitbucketHook
}


def hook_by_id(service_id):
    """
    Returns a HookService given it's internal id, or ``None`` if it
    could not be found.
    """
    return _default_hooks.get(service_id, None)


def registered_hooks():
    """
    Returns a list of all registered HookService's.
    """
    return _default_hooks.values()
