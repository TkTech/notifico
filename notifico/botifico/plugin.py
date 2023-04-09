from collections import defaultdict
from typing import Dict, Set, Callable, Union

from notifico.botifico.events import Event


class Plugin:
    event_receivers: Dict[str, Set[Callable]]
    name: str

    def __init__(self, name):
        """
        Creates a new Plugin, which can be used to re-use event handlers
        across different bots.

        :param name: A globally-unique name for this plugin.
        """
        self.event_receivers = defaultdict(set)
        self.name = name

    def on(self, event: Union[str, Event], block: bool = False):
        """
        A decorator which registers an event handler for `message`.

        If `block` is `True`, the event handler will be called synchronously
        instead of executed in its own task.
        """
        event = event.value if isinstance(event, Event) else event.upper()

        def _f(f):
            # We should probably just store this in the set.
            f.plugin = self
            # Yep this too.
            f.plugin_should_block = block
            self.event_receivers[event].add(f)
            return f

        return _f

    @property
    def metadata_key(self):
        return self.name

    def get(self, bot, key, default=None):
        v = bot.plugin_metadata[self.metadata_key].get(key, default)
        return v() if callable(v) else v

    def set(self, bot, key, value):
        bot.plugin_metadata[self.metadata_key][key] = value
