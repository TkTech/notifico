import functools
from importlib.metadata import entry_points
from typing import Dict

from notifico.services.hook import HookService


@functools.cache
def available_services() -> Dict[int, HookService]:
    """
    Returns a cached dictionary of all discoverable service plugins.
    """
    eps = entry_points().select(group='notifico.plugins.service')  # noqa

    return {
        h.SERVICE_ID: h
        for h in (ep.load() for ep in eps)
    }
