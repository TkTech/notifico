import json

import redis.asyncio as redis

from notifico.botifico.bot import Bot, Network
from notifico.botifico.contrib.plugins.identity import identity_plugin
from notifico.botifico.contrib.plugins.logging import log_plugin
from notifico.botifico.plugin import Plugin
from notifico.botifico.manager import Manager, Channel
from notifico.botifico.contrib.plugins.ping import ping_plugin


from notifico.settings import Settings


handshake = Plugin('handshake')


async def process_messages(r, manager: Manager):
    """
    Process as many messages on the message queue as possible.
    """
    while True:
        v = await r.lpop('messages')
        if v is None:
            return

        j = json.loads(v.decode('utf-8'))

        match j['type']:
            case 'message':
                # We've received a message destined for an IRC channel.
                channel = j['channel']

                c = await manager.channel(
                    Network(
                        channel['host'],
                        channel['port'],
                        channel['ssl']
                    ),
                    Channel(
                        channel['channel'],
                        password=channel.get('channel_password')
                    )
                )

                await c.private_message(j['payload']['msg'])
            case 'cnc':
                # We've received a command-and-control message.
                pass


async def wait_for_events():
    """
    Connects to Redis and waits for messages to get pushed to the queue.

    Once messages are received, they're pushed to a Manager.

    .. note::

        For this to work efficiently, Redis needs to have event emitting
        enabled. Use `CONFIG SET notify-keyspace-events Kl` to enable
        [K]eyspace events for [l]ist commands.
    """
    settings = Settings()

    manager = Manager('botifico')
    manager.register_plugin(ping_plugin)
    manager.register_plugin(identity_plugin)
    manager.register_plugin(log_plugin)

    r = await redis.from_url(settings.REDIS)

    # Before we start waiting for events, process anything already in the
    # queue.
    await process_messages(r, manager)

    notifications: redis.client.PubSub = r.pubsub()
    # We listen to a special notifications PubSub channel which will trigger
    # whenever an operation occurs on our messages queue.
    await notifications.subscribe('__keyspace@0__:messages')

    async for message in notifications.listen():
        match message['type']:
            case 'subscribe':
                continue
            case 'message':
                match message['data']:
                    case b'rpush':
                        # New data has been pushed to the messages queue, try
                        # to snag it.
                        await process_messages(r, manager)
