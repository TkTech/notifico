"""
Contains the main Notifico IRC bot implementation built on top of Botifico.
"""
import asyncio
import json
import traceback
from typing import Any, Dict

import sentry_sdk
import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from notifico import create_app
from notifico.botifico.bot import Bot, Network
from notifico.botifico.contrib.plugins.identity import identity_plugin
from notifico.botifico.contrib.plugins.logging import log_plugin
from notifico.botifico.contrib.plugins.rate_limit import rate_limit_plugin
from notifico.botifico.plugin import Plugin
from notifico.botifico.manager import Manager, Channel
from notifico.botifico.contrib.plugins.ping import ping_plugin


from notifico.settings import Settings


handshake = Plugin('handshake')


def _get_channel(j):
    channel = j['channel']
    return Channel(channel['channel'], password=channel.get('channel_password'))


def _get_network(j):
    channel = j['channel']
    return Network(channel['host'], channel['port'], channel['ssl'])


async def _handle_single_message(j: Dict[str, Any], manager: Manager):
    match j['type']:
        case 'message':
            # Incoming message destined for a specific IRC channel.
            network = _get_network(j)
            channel = _get_channel(j)
            try:
                c = await manager.channel(network, channel)
                await c.private_message(j['payload']['msg'])
            except Exception as exception:
                sentry_sdk.capture_exception(exception)
                traceback.print_exc()
        case 'start-logging':
            # Enable logging on an already-connected channel.
            raise NotImplementedError()
        case 'stop-logging':
            # Disable logging on an already-connected channel.
            raise NotImplementedError()


async def process_messages(r, manager: Manager):
    """
    Process as many messages on the message queue as possible.
    """
    while True:
        v = await r.lpop('messages')
        if v is None:
            return

        j = json.loads(v.decode('utf-8'))
        asyncio.create_task(_handle_single_message(j, manager))


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
    app = create_app()

    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN)

    with app.app_context():
        manager = Manager('botifico')
        manager.register_plugin(ping_plugin)
        manager.register_plugin(identity_plugin)
        manager.register_plugin(log_plugin)
        manager.register_plugin(rate_limit_plugin)

        r = await redis.from_url(
            settings.REDIS,
            retry=Retry(
                NoBackoff(),
                50
            )
        )

        # TODO: Proactively retrieve all channels which have logging setup,
        #       and ensure we join them ASAP.

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
                            # New data has been pushed to the messages queue,
                            # try to snag it.
                            await process_messages(r, manager)
