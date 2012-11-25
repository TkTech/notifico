# -*- coding: utf8 -*-
import json
from Queue import Empty
from collections import defaultdict
from multiprocessing import Process, Queue

import redis

from botifico import default_config as config
from botifico.bot import Bot


class BotState(object):
    def __init__(self):
        self._bots = defaultdict(list)

    def bot_for_channel(self, network, channel, port=6667, ssl=False):
        bots = self.bots_for_network(network, port, ssl)
        if not bots:
            bot = self.create_bot(network, port, ssl)
        else:
            # TODO: Check maximum channel count.
            bot = bots[-1]
        return bot

    def bots_for_network(self, network, port=6667, ssl=False):
        return self._bots.get((network, port, ssl))

    def create_bot(self, network, port=6667, ssl=False):
        b = Bot(host=network, port=port, use_ssl=ssl)
        b.connect()
        self._bots[(network, port, ssl)].append(b)
        return b

    def send_to_channel(self, message, channel, network, port, ssl):
        bot = self.bot_for_channel(network, channel, port, ssl)
        bot.send_message(channel, message)


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

    bs = BotState()
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
