# -*- coding: utf8 -*-
import json

import redis
import gevent
from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

from notifico.bots.util import Network, Channel
from notifico.bots.manager import BotManager
from notifico.bots.bot import BotificoBot
from notifico.settings import Settings


def start_manager():
    settings = Settings()

    if settings.SENTRY_DSN:
        handler = SentryHandler(settings.SENTRY_DSN)
        setup_logging(handler)

    r = redis.StrictRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB
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
