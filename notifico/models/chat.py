import datetime
import enum

import sqlalchemy as sa
from flask import url_for
from sqlalchemy import orm
from sqlalchemy.dialects.postgresql import JSONB

from notifico.database import Base


class ChatLog(Base):
    """
    Represents a collection of log messages from sources like IRC channels.

    For privacy and simplicity, if logging is enabled, it is always considered
    public and this is communicated to the user and the channel (if possible).
    Allowing a channel to be private, and then become public, introduces
    chances for bugs to display messages to the public that were not expected
    to ever be visible.

    These log messages will most likely only ever capture from IRC and
    protocols like Matrix or XMPP, given the restrictive nature of Slack,
    Discord, Teams, etc..., so we do not need to consider them when making
    changes.
    """

    class Page(enum.IntEnum):
        DETAILS = 10

    __tablename__ = "chat_log"

    id = sa.Column(sa.Integer, primary_key=True)

    # Several users may all have different instances of a channel, say
    # #commits, which will all link to a single log.
    channels = orm.relationship(
        "Channel", lazy="dynamic", backref=orm.backref("chat_log")
    )

    messages = orm.relationship(
        "ChatMessage",
        lazy="dynamic",
        cascade="all, delete-orphan",
        backref=orm.backref("chat_log"),
    )

    # A cached count of all the lines logged in this ChatLog. This should
    # be atomically incremented whenever a new ChatMessage is created.
    line_count = sa.Column(sa.BigInteger, default=0)

    created = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)

    def url(self, of: Page = Page.DETAILS) -> str:
        match of:
            case self.Page.DETAILS:
                return url_for("chat.details", log_id=self.id)
            case _:
                raise ValueError(f"Don't know how to generate a URL for {of=}.")


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id = sa.Column(sa.BigInteger, primary_key=True)

    log_id = sa.Column(sa.Integer, sa.ForeignKey("chat_log.id"))

    # The content of the message, as a JSON object. This is intended to be
    # a "raw" representation of the message, and should be parsed by the
    # client. This is to allow for the most flexibility in the future.
    message = sa.Column(JSONB)

    # A string label for the message sender, if there is one. It may not be
    # present in the case of system or service messages. This is not intended
    # to be "accurate" or to track a user - users on IRC may change their name
    # as often as they want, for example. It is solely to enable searching
    # message logs by name easier.
    sender = sa.Column(sa.String(256), nullable=True)

    # The time this message was originally sent.
    timestamp = sa.Column(sa.TIMESTAMP())

    __table_args__ = (
        # Message lookup is almost always going to be in chronological order
        # within a single ChatLog.
        sa.Index("idx_log_id_and_ts", timestamp.desc(), log_id),  # noqa
    )
