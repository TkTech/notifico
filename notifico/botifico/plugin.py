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
        """
        event = event.value if isinstance(event, Event) else event.upper()

        def _f(f):
            f.plugin = self
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
