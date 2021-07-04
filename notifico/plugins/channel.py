import enum
import dataclasses
from typing import List

import flask_wtf


class ChannelTrigger(enum.Enum):
    #: A Channel with this type of trigger cannot ever be triggered.
    NONE = 0
    #: A Channel with this type of trigger can be hit by a webhook.
    WEBHOOK = 1
    #: A Channel with this type of trigger will be periodically triggered.
    PERIODIC = 2


@dataclasses.dataclass
class MessageBase:
    pass


@dataclasses.dataclass
class TextMessage(MessageBase):
    """
    A simple text message, used as the fallback format for most providers
    when a more specific format was not available.
    """
    #: A list of individual lines. Channels may decide to truncate a line
    #: if it exceeds certain lengths (ex: IRC) or wrap it around to a new
    #: line.
    lines: List[str] = dataclasses.field(default_factory=list)
    #: An optional prefix to be attached to every line.
    prefix: str = ''


class OutboundForm(flask_wtf.FlaskForm):
    """
    A base form most outbound channels should use for their configuration
    options.
    """


class InboundForm(flask_wtf.FlaskForm):
    """
    A base form most inbound channels should use for their configuration
    options.
    """


class ChannelPlugin:
    CHANNEL_NAME: str = None
    CHANNEL_DESCRIPTION: str = None
    CHANNEL_TRIGGER: ChannelTrigger.NONE

    @classmethod
    def user_form(cls):
        """
        An optional FlaskForm *class* (not an instance!) that will be
        presented to an end user when they are configuring this Channel.
        """


class OutboundChanel(ChannelPlugin):
    @classmethod
    def handle_message(cls, messages: List[MessageBase]):
        """
        Deliver one of the provided messages to a destination. When multiple
        messages are provided, the Channel should use the most specific
        possible, falling back to a simple TextMessage if nothing more specific
        was provided.
        """
        raise NotImplementedError()

    @classmethod
    def user_form(cls):
        return OutboundForm


class InboundChannel(ChannelPlugin):
    """
    You should never subclass an _InboundChannel directly. Use one of its
    subclasses instead.
    """
    @classmethod
    def user_form(cls):
        return InboundForm


class InboundWebhookChannel(InboundChannel):
    CHANNEL_TRIGGER = ChannelTrigger.WEBHOOK

    @classmethod
    def pack_request(cls, request) -> bytes:
        """
        Turn the payload of the given request into a `bytes` object that will
        be sent to the background worker for this webhook.

        Typically, this would be taking the JSON payload of a webhook and
        simply passing it along.

        It's important this method return as quickly as possible, as it's
        invoked directly by a webhook.
        """
        raise NotImplementedError()

    @classmethod
    def handle_request(cls, request):
        """
        Handle the given incoming request, emitting 0 or more Messages for
        outbound channels to consume.

        .. note::

            This method will run in a background worker pool, and has no access
            to the original request beyond what was packed in
            :func:`pack_request`.
        """
        raise NotImplementedError()


class InbountPeriodicChannel(InboundChannel):
    """
    The base class for periodicly polling channels. This can be used to
    implement channels for services which do not support webhooks or other
    methods of near-realtime notification.

    It's important to note that a periodic channel has no real-time guarantees.
    It will run _no sooner_ than it's polling period, but may run significantly
    after.

    Whenever possible, periodic channels hitting remote resources should use a
    global cache key to avoid situations like 300 periodic tasks all hitting
    wikipedia at the same time.
    """
    CHANNEL_TRIGGER = ChannelTrigger.PERIODIC

    @classmethod
    def polling_period(cls):
        """
        For `ChannelTrigger.PERIODIC`-type Channels, this is the *minimum*
        time at which it should be scheduled. Channels are not guaranteed
        to occur at that time, only that they'll occur *after* this time.
        """
        raise NotImplementedError()

    @classmethod
    def handle_tick(cls):
        """
        Triggered after the minimum polling period has elapsed. Should perform
        the configured task, emitting 0 or more Messages for `OUTBOUND`
        channels.

        .. note::

            This method will run in a background worker pool.
        """
        raise NotImplementedError()
