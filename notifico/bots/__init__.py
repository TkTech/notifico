# -*- coding: utf8 -*-
import json

import redis
import gevent
from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

from notifico.bots.manager import BotManager, Channel, Network
from notifico.bots.bot import BotificoBot
import notifico.default_config as config


def start_manager():
    if config.SENTRY_DSN:
        handler = SentryHandler(config.SENTRY_DSN)
        setup_logging(handler)

    r = redis.StrictRedis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB
    )
    manager = BotManager(BotificoBot)

    while True:
        result = r.lpop('queue_message')
        if result:
            m = json.loads(result)
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

        gevent.sleep(0.1)

if __name__ == '__main__':
    start_manager()
