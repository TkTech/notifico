# -*- coding: utf8 -*-
import json
from Queue import Empty
from multiprocessing import Process, Queue

import redis

import notifico.default_config as config


def wait_for_message(q):
    """
    Wait for a new message to be forwarded.
    """
    r = redis.StrictRedis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB
    )

    while True:
        _, message = r.blpop('queue_message')
        q.put(json.loads(message))


def start_manager():
    q = Queue()
    p = Process(target=wait_for_message, args=(q,))
    p.start()

    import gevent
    from utopia import Network
    from notifico.bots.manager import BotManager, Channel
    from notifico.bots.bot import BotificoBot

    manager = BotManager(BotificoBot)

    while True:
        try:
            m = q.get(False)
            if m['type'] == 'message':
                channel = m['channel']
                payload = m['payload']

                manager.send_message(
                    Network(
                        host=channel['host'],
                        port=channel['port'],
                        ssl=channel['ssl'],
                        password=channel.get('password', None)
                    ),
                    Channel(
                        channel=channel['channel'],
                        password=channel.get('channel_password', None)
                    ),
                    payload['msg']
                )
        except Empty:
            pass

        gevent.sleep(0.1)

if __name__ == '__main__':
    start_manager()
