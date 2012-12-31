# -*- coding: utf8 -*-
__all__ = ('MessageService',)
import json


class MessageService(object):
    #: Key name for the outgoing message queue.
    key_queue_messages = 'queue_message'
    #: Key name for recent messages.
    key_recent_messages = 'recent_messages'

    def __init__(self, redis=None):
        self._redis = redis

    @property
    def r(self):
        return self._redis

    def recent_messages(self, start=0, stop=-1):
        """
        Returns a list of recent messages from `start` to `stop`.
        """
        if not self.r:
            return []

        return [
            json.loads(m) for m in self.r.lrange(
                self.key_recent_messages, start, stop
            )
        ]

    def send_message(self, message, channel):
        """
        Sends `message` to `channel`.
        """
        final_message = {
            # What we're delivering.
            'type': 'message',
            # Contents of the message.
            'payload': {
                'msg': message
            },
            # Destination.
            'channel': {
                'channel': channel.channel,
                'host': channel.host,
                'port': channel.port,
                'ssl': channel.ssl
            }
        }
        message_dump = json.dumps(final_message)
        self.r.rpush(self.key_queue_messages, message_dump)

    def log_message(self, message, project, log_cap=200):
        """
        Log up to `log_cap` messages,
        """
        final_message = {
            'msg': message,
            'project_id': project.id,
            'owner_id': project.owner.id
        }
        message_dump = json.dumps(final_message)

        with self.r.pipeline() as pipe:
            pipe.lpush(self.key_recent_messages, message_dump)
            pipe.ltrim(self.key_recent_messages, 0, log_cap)
            pipe.execute()
