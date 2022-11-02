import functools
from importlib.metadata import entry_points
from typing import Dict

from notifico.services.hook import IncomingHookService, OutgoingHookService


@functools.cache
def outgoing_services() -> Dict[int, OutgoingHookService]:
    """
    Returns a cached dictionary of all discoverable outgoing services.
    """
    eps = entry_points().select(group='notifico.plugins.outgoing')  # noqa
    return {h.SERVICE_ID: h for h in (ep.load() for ep in eps)}


@functools.cache
def incoming_services() -> Dict[int, IncomingHookService]:
    """
    Returns a cached dictionary of all discoverable incoming services.
    """
    eps = entry_points().select(group='notifico.plugins.incoming')  # noqa
    return {h.SERVICE_ID: h for h in (ep.load() for ep in eps)}
