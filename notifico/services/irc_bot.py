"""
Contains the main Notifico IRC bot implementation built on top of Botifico.
"""
import asyncio
import datetime
import json
import traceback
from typing import Any, Dict, Iterable

import sentry_sdk
import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
import sqlalchemy as sa

from notifico import create_app, db_session
from notifico.botifico.bot import Bot, Network
from notifico.botifico.contrib.plugins.identity import identity_plugin
from notifico.botifico.contrib.plugins.logging import log_plugin
from notifico.botifico.contrib.plugins.rate_limit import rate_limit_plugin
from notifico.botifico.events import Event
from notifico.botifico.parsing import Prefix
from notifico.botifico.plugin import Plugin
from notifico.botifico.manager import ChannelBot, ChannelProxy, Manager, Channel
from notifico.botifico.contrib.plugins.ping import ping_plugin
from notifico.models import ChatLog, ChatMessage, IRCNetwork, NetworkEvent
from notifico.models import Channel as ChannelModel

from notifico.settings import Settings


# The tracker plugin is used to track the bot's current state in the database,
# such as connected and disconnected events.
tracker = Plugin('tracker')
# The chat_logger plugin does exactly what it says, logging the chat and
# general actions (JOIN, PART, etc.) to the database when a channel is set up.
# for logging.
chat_logger = Plugin('chat_logger')


def _get_matching_networks(network: Network) -> Iterable[IRCNetwork]:
    return db_session.query(
        IRCNetwork
    ).filter(
        IRCNetwork.host == network.host,
        IRCNetwork.port == network.port,
        IRCNetwork.ssl == network.ssl
    )


@tracker.on(Event.on_connected)
async def on_connect(bot: Bot):
    for network in _get_matching_networks(bot.network):
        db_session.add(NetworkEvent(
            network=network,
            event=NetworkEvent.Event.INFO,
            description='Connected to IRC network.'
        ))

    db_session.commit()


@tracker.on(Event.on_disconnect)
async def on_disconnect(bot: Bot):
    for network in _get_matching_networks(bot.network):
        db_session.add(NetworkEvent(
            network=network,
            event=NetworkEvent.Event.INFO,
            description='Disconnected from IRC network.'
        ))

    db_session.commit()


@chat_logger.on(Event.on_message)
async def on_message(bot: ChannelBot, command: str, args, prefix: Prefix):
    # TODO: We should be caching in here, and relying on the start-logging
    #       and stop-logging signals to invalidate it. However, for now volume
    #       is low enough that we can just query the database every time.
    if command not in ('PRIVMSG',):
        return

    channel: ChannelProxy | None = bot.get_channel(args[0])
    if not channel or channel.channel.password:
        # We don't log messages to channels that are password protected.
        # This is to prevent someone from trying to create a custom network
        # that overlaps with another network, and then logging all messages
        # to a channel that shouldn't actually be public.
        return

    # Find all the database-backed Channels that match the current IRC channel.
    channels = db_session.query(
        ChannelModel
    ).join(
        ChannelModel.network
    ).filter(
        IRCNetwork.host == bot.network.host,
        IRCNetwork.port == bot.network.port,
        IRCNetwork.ssl == bot.network.ssl
    ).filter(
        ChannelModel.channel == channel.channel.name,
        ChannelModel.logged.is_(True),
        ChannelModel.public.is_(True),
        sa.or_(
            ChannelModel.password.is_(None),
            ChannelModel.password == ""
        ),
    ).all()

    # In theory every Channel that matches should have the same ChatLog.
    chat_log = db_session.query(
        ChatLog
    ).filter(
        ChatLog.channels.any(
            ChannelModel.id.in_([c.id for c in channels])
        )
    ).first()
    if chat_log is None:
        chat_log = ChatLog()
        chat_log.channels.extend(channels)

    chat_log.line_count = ChatLog.line_count + 1
    db_session.add(chat_log)
    db_session.add(
        ChatMessage(
            chat_log=chat_log,  # noqa, PyCharm doesn't understand this.
            message=args[1],
            sender=prefix.nick,
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc)
        )
    )
    db_session.commit()


async def _handle_single_message(j: Dict[str, Any], manager: Manager):
    match j['type']:
        case 'message':
            # Incoming message destined for a specific IRC channel.
            channel = db_session.query(ChannelModel).get(j['channel'])

            try:
                c = await manager.channel(
                    Network(
                        channel.network.host,
                        channel.network.port,
                        channel.network.ssl
                    ),
                    Channel(channel.channel, password=channel.password)
                )
                await c.private_message(j['payload']['msg'])
            except Exception as exception:
                sentry_sdk.capture_exception(exception)
                traceback.print_exc()
        case 'start-logging':
            # Enable logging on an already-connected channel.
            channel = db_session.query(ChannelModel).get(j['channel'])

            try:
                c = await manager.channel(
                    Network(
                        channel.network.host,
                        channel.network.port,
                        channel.network.ssl
                    ),
                    Channel(channel.channel, password=channel.password)
                )
                await c.join()
            except Exception as exception:
                sentry_sdk.capture_exception(exception)
                traceback.print_exc()
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
        manager.register_plugin(tracker)
        manager.register_plugin(chat_logger)

        r = await redis.from_url(
            settings.REDIS,
            retry=Retry(
                NoBackoff(),
                50
            )
        )

        # If someone is using redis for something else, we probably don't want
        # to clobber their config but for our purposes, we need to enable
        # keyspace events.
        await r.config_set('notify-keyspace-events', 'Kl')

        # TODO: Proactively retrieve all channels which have logging setup,
        #       and ensure we join them ASAP.

        # Before we start waiting for events, process anything already in the
        # queue.
        await process_messages(r, manager)

        notifications: redis.client.PubSub = r.pubsub()
        # We listen to a special notifications PubSub channel which will trigger
        # whenever an operation occurs on our messages queue.
        await notifications.subscribe('__keyspace@0__:messages')

        async for message in notifications.listen():  # noqa
            match message['type']:
                case 'subscribe':
                    continue
                case 'message':
                    match message['data']:
                        case b'rpush':
                            # New data has been pushed to the messages queue,
                            # try to snag it.
                            await process_messages(r, manager)
