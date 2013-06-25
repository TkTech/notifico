# -*- coding: utf-8 -*-
"""
Service for working with password resets.
"""
import uuid

from flask import current_app


_tokens_by_user = lambda u: 'pw_reset_tokens_{uid}'.format(uid=u.id)


def _generate_token():
    return uuid.uuid4().hex


def tokens_for_user(user):
    return current_app.redis.lrange(_tokens_by_user(user), 0, -1)


def count_tokens(user):
    return current_app.redis.llen(_tokens_by_user(user))


def valid_token(user, token):
    return token in tokens_for_user(user)


def add_token(user, max_tokens=5, expire=60 * 60 * 24):
    """
    Creates and records a new reset token for
    """
    r = current_app.redis

    new_token = _generate_token()
    token_key = _tokens_by_user(user)
    already_exists = r.exists(token_key)

    pipe = r.pipeline()
    pipe.lpush(token_key, new_token)
    pipe.ltrim(token_key, 0, max_tokens - 1)

    if not already_exists:
        # Only set/reset the expiry if the key didn't already
        # exist.
        pipe.expire(token_key, expire)

    pipe.execute()

    return new_token


def clear_tokens(user):
    current_app.redis.delete(_tokens_by_user(user))
