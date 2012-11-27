# -*- coding: utf8 -*-
import json
import signal
from Queue import Empty
from collections import defaultdict
from multiprocessing import Process, Queue

import redis

from notifico import db, start
from notifico.models import BotEvent

from botifico import default_config as config
from botifico.bot import Bot


class BotState(object):
    def __init__(self, redis):
        self._bots = defaultdict(list)
        self._redis = redis

    def bot_for_channel(self, network, channel, port=6667, ssl=False):
        """
        Returns or creates a bot suitable for use on `network`:`port` in
        `channel`, optionally using SSL.
        """
        bots = self.bots_for_network(network, port, ssl)
        if not bots:
            bot = self.create_bot(network, port, ssl)
        else:
            # TODO: Check maximum channel count.
            bot = bots[-1]
        return bot

    def bots_for_network(self, network, port=6667, ssl=False):
        """
        Return a list of bots active on `network`:`port`.
        """
        return self._bots.get((network, port, ssl))

    def create_bot(self, network, port=6667, ssl=False):
        """
        Create a new bot and connect it for `network`:`port`, optionally
        using SSL.
        """
        b = Bot(self, host=network, port=port, use_ssl=ssl)
        self.bot_event(b, 'Connecting...', 'connect', 'ok')
        b.connect()
        self.bot_event(b, 'Connected.', 'connect', 'ok')
        self._bots[(network, port, ssl)].append(b)
        return b

    def send_to_channel(self, message, channel, network, port, ssl):
        """
        Send the given `message` to `channel` on `network`:`port`, optionally
        using SSL.
        """
        bot = self.bot_for_channel(network, channel, port, ssl)
        bot.send_message(channel, message)

    def bot_event(self, bot, message, event, status, channel=None):
        """
        Send a bot event (such as a disconnect or kick) to redis.
        """
        b = BotEvent.new(
            host=bot.address[0],
            port=bot.address[1],
            ssl=bot.use_ssl,
            message=message,
            event=event,
            status=status,
            channel=channel
        )
        db.session.add(b)
        db.session.commit()


def wait_for_message(q):
    """
    Wait for messages from Redis PubSub.
    """
    r = redis.StrictRedis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB
    )

    ps = r.pubsub()
    ps.subscribe('message')

    for message in ps.listen():
        if message['type'] == 'message':
            q.put(json.loads(message['data']))


def start_manager():
    import gevent

    # Setup (but don't *really*) start Notifico so that our
    # database configuration is completely loaded.
    start()

    gevent.signal(signal.SIGQUIT, gevent.shutdown)

    r = redis.StrictRedis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB
    )

    bs = BotState(r)
    q = Queue()
    p = Process(target=wait_for_message, args=(q,))
    p.start()

    while True:
        try:
            m = q.get(False)
            if m['type'] == 'message':
                channel = m['channel']
                payload = m['payload']

                bs.send_to_channel(
                    payload['msg'],
                    channel['channel'],
                    channel['host'],
                    channel['port'],
                    channel['ssl']
                )
        except Empty:
            pass

        gevent.sleep(0.5)
