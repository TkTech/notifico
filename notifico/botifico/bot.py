import inspect
import asyncio
import dataclasses
from collections import defaultdict
from functools import wraps
from typing import Optional, Dict, Set, Callable, Union, Iterable

from notifico.botifico.errors import ReadExceededError
from notifico.botifico.events import Event
from notifico.botifico.logger import logger
from notifico.botifico.parsing import unpack_message
from notifico.botifico.plugin import Plugin


@dataclasses.dataclass(frozen=True)
class Network:
    host: str
    port: int
    ssl: bool


def exception_catcher(f: Callable):
    @wraps(f)
    async def _wrapped(self: 'Bot', *args, **kwargs):
        try:
            return await f(self, *args, **kwargs)
        except Exception as exc:
            await self.task_exception(exc)
            raise
    return _wrapped


class Bot:
    network: Network
    event_receivers: Dict[str, Set[Callable]]
    event_emitters: Dict[str, asyncio.Event]
    plugin_metadata: Dict[str, dict]

    def __init__(self, network: Network, *, max_buffer_size=0x100000):
        """
        A minimal IRC "bot".

        By default, this handles nothing except the socket IO. Event handlers
        must be registered to implement basic functionality.
        """
        self.network = network
        self.message_queue = asyncio.Queue()
        self.event_receivers = defaultdict(set)
        self.event_emitters = defaultdict(lambda: asyncio.Event())
        self.plugin_metadata = defaultdict(dict)
        self.max_buffer_size = max_buffer_size

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.network!r})>'

    @exception_catcher
    async def connect(self):
        """
        Attempts to connect the bot to its network and starts processing
        events.
        """
        logger.info(f'[Core] Attempting to connect to {self.network!r}')

        reader, writer = await asyncio.open_connection(
            host=self.network.host,
            port=self.network.port,
            ssl=self.network.ssl,
            limit=self.max_buffer_size
        )

        await self.emit_event(Event.on_connected)
        message_so_far = ''

        read_chunk = asyncio.create_task(reader.read(512))
        get_queue = asyncio.create_task(self.message_queue.get())
        while True:
            # Wait until either there's network traffic to read, or there's a
            # message waiting to be sent.
            done, pending = await asyncio.wait(
                [read_chunk, get_queue],
                return_when=asyncio.FIRST_COMPLETED
            )

            if read_chunk in done:
                chunk: Optional[bytes] = read_chunk.result()

                # Remote server closed the connection.
                if chunk == b'':
                    self.message_queue.empty()
                    await self.emit_event(Event.on_disconnect)

                    for task in pending:
                        if not task.cancelled():
                            task.cancel()

                    return

                message_so_far += chunk.decode('utf-8')
                if len(message_so_far) > self.max_buffer_size:
                    # Realistically, the only time this is actually going to
                    # happen is when connection to a malicious server, so lets
                    # just die.
                    raise ReadExceededError()

                while '\r\n' in message_so_far:
                    line, message_so_far = message_so_far.split('\r\n', 1)
                    prefix, command, args = unpack_message(line)
                    await self.emit_event(
                        Event.on_message,
                        command=command.upper(),
                        args=args,
                        prefix=prefix
                    )
                    await self.emit_event(
                        command.upper(),
                        args=args,
                        prefix=prefix
                    )

                read_chunk = asyncio.create_task(reader.read(512))

            if get_queue in done:
                to_be_sent = get_queue.result()
                await self.emit_event(Event.on_write, message=to_be_sent)
                writer.write(to_be_sent)
                # We should probably write what we can and then continue our
                # loop to ensure we're always reading, but for now we wait
                # until we've written everything.
                await writer.drain()
                get_queue = asyncio.create_task(self.message_queue.get())

    async def task_exception(self, ex: Exception):
        await self.emit_event(Event.on_exception, ex=ex)
        raise ex

    async def emit_event(self, event: Union[str, Event], **kwargs):
        """
        Emit the given event to all registered handlers.
        """
        if isinstance(event, Event):
            event = event.value

        kwargs['bot'] = self

        for handler in self.event_receivers[event]:
            # Only pass the arguments the handler has specified.
            sig = inspect.signature(handler)

            # When event handlers are registered on a plugin, we store the
            # registering plugin on the function as `plugin`.
            kwargs['plugin'] = getattr(handler, 'plugin', None)

            await handler(**{
                k: v for k, v in kwargs.items()
                if k in sig.parameters
            })

        # Trigger and immediately clear anything waiting on events.
        ev = self.event_emitters[event]
        ev.set()
        ev.clear()

    async def send(self, command: str, *args):
        await self.send_raw(f'{" ".join((command, *args))}\r\n'.encode())

    async def send_raw(self, message: bytes):
        await self.message_queue.put(message)

    async def wait_for(self, event: Union[str, Event]):
        if isinstance(event, Event):
            event = event.value
        return await self.event_emitters[event].wait()

    async def wait_for_any(self, events: Iterable[Union[str, Event]], *,
                           timeout: Optional[int] = None):
        return asyncio.wait([
            self.event_emitters[
                event.value if isinstance(event, Event) else event
            ].wait()
            for event in events
        ], return_when=asyncio.FIRST_COMPLETED, timeout=timeout)

    def register_plugin(self, plugin: Plugin):
        """
        Registers a plugin's event handlers with this bot.
        """
        for key in plugin.event_receivers.keys():
            self.event_receivers[key].update(plugin.event_receivers[key])

    def unregister_plugin(self, plugin: Plugin):
        """
        Unregisters a plugin's event handlers with this bot.
        """
        for key in plugin.event_receivers.keys():
            self.event_receivers[key] -= plugin.event_receivers[key]

    def register_handler(self, event: Union[str, Event], f: Callable):
        """
        Register an event handler with this bot.
        """
        event = event.value if isinstance(event, Event) else event.upper()
        self.event_receivers[event].add(f)

    def unregister_handler(self, event: Union[str, Event], f: Callable):
        """
        Unregisters an event handler with this bot.
        """
        event = event.value if isinstance(event, Event) else event.upper()
        self.event_receivers[event].remove(f)
