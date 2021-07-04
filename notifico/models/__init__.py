from notifico.models.user import User
from notifico.models.project import Project
from notifico.models.log import Log, LogContext
from notifico.models.channel import Channel
from notifico.models.group import Group, Permission, Limit
from notifico.models.plugin import Plugin

# We use this so tools like alembic can find all the models we use, even if
# they're not necessarily imported by the time it runs.
#: All models used in the core.
ALL_MODELS = (
    Log,
    LogContext,
    User,
    Project,
    Group,
    Permission,
    Limit,
    Channel,
    Plugin
)
