from notifico.models.user import User, Role, Permission
from notifico.models.channel import Channel, IRCNetwork, NetworkEvent
from notifico.models.hook import Hook
from notifico.models.project import Project

ALL_MODELS = [
    User,
    Role,
    Permission,
    Channel,
    IRCNetwork,
    Hook,
    Project,
    NetworkEvent
]
