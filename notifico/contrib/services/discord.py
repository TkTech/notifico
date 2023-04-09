from notifico.contrib.services import EnvironmentMixin
from notifico.services.hook import OutgoingHookService, StructuredMessage


class DiscordHook(EnvironmentMixin, OutgoingHookService):
    """
    Simple service hook that just accepts text.
    """

    SERVICE_ID = 5100
    SERVICE_NAME = "Discord"

    @classmethod
    def handle_message(cls, message: StructuredMessage):
        pass
