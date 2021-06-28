from flask_wtf import FlaskForm

from notifico.models.provider import Provider


class TargetBaseForm(FlaskForm):
    pass


class MessageBase:
    pass


class TextMessage(MessageBase):
    pass


class TargetImplementation:
    """
    A Target is any destination for messages, such as IRC or Discord. Each
    target defines its own message container, which can be used for richer,
    target-specific output then the default simple text message.
    """
    #: The preferred message class for this target.
    Message = TextMessage

    @classmethod
    def handle_message(cls, provider: Provider, message: Message):
        """
        Delivers a message from the given provider to the Target.

        :param provider: The Provider which is issuing the Message.
        :param message: The Message to be delivered.
        """
        raise NotImplementedError()
